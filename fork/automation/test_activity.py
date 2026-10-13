"""Exercise the real Automation callback and ORM using disposable SQLite."""

import importlib.util
import json
import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from callback_metadata import merge_callback_metadata, normalize_task_outcome
from fastapi import HTTPException, Request
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from openhands.automation.auth import AuthenticatedUser, AuthMethod
from openhands.automation.models import (
    Automation,
    AutomationRun,
    AutomationRunStatus,
    Base,
)
from openhands.automation.router import complete_run
from openhands.automation.schemas import RunCompleteRequest


logging.disable(logging.INFO)


class MetadataTests(unittest.TestCase):
    def test_preserves_finish_and_owner_without_mutation(self):
        existing = {"owner": "keep", "finish_tool_response": {"message": "real"}}
        result = merge_callback_metadata(
            existing, {"status": "blocked", "outcome_summary": "gate"}
        )
        self.assertEqual(result["owner"], "keep")
        self.assertEqual(
            result["finish_tool_response"],
            {"message": "real", "status": "blocked", "outcome_summary": "gate"},
        )
        self.assertEqual(existing["finish_tool_response"], {"message": "real"})

    def test_unknown_redaction_and_size(self):
        outcome = normalize_task_outcome(
            {
                "status": "invalid",
                "outcome_summary": "Bearer sample-secret-value",
                "token": "drop",
                "payload": "😀" * 10000,
            }
        )
        self.assertEqual(outcome["status"], "unknown")
        self.assertNotIn("token", outcome)
        self.assertNotIn("sample-secret-value", outcome["outcome_summary"])
        self.assertNotIn("processed", outcome)
        self.assertLessEqual(len(json.dumps(outcome).encode()), 8192)

    @unittest.skipUnless(
        os.environ.get("PRODUCTION_CALLBACK_MODULE"), "optional deployed-module parity"
    )
    def test_deployed_module_parity(self):
        spec = importlib.util.spec_from_file_location(
            "deployed_callback", os.environ["PRODUCTION_CALLBACK_MODULE"]
        )
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        for value in [
            None,
            {},
            {"status": "success", "processed": 0},
            {
                "status": "blocked",
                "outcome_summary": "gate",
                "headers": {"Authorization": "secret"},
            },
            {"outcome_summary": "😀" * 10000, "values": list(range(50))},
        ]:
            existing = {
                "ownership": "kept",
                "finish_tool_response": {"message": "real", "custom": 3},
            }
            self.assertEqual(
                merge_callback_metadata(existing, value),
                original.merge_callback_metadata(existing, value),
            )


class CallbackTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///" + str(Path(self.tmp.name) / "test.db")
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.user_id, self.org_id = uuid4(), uuid4()
        self.run_id = uuid4()
        self.user = AuthenticatedUser(
            self.user_id,
            self.org_id,
            "test@example.com",
            "admin",
            ["view_automations"],
            AuthMethod.API_KEY,
        )
        async with self.sessions() as session:
            auto = Automation(
                user_id=self.user_id,
                org_id=self.org_id,
                name="isolated",
                trigger={"type": "manual"},
                tarball_path="https://example.com/test.tar",
                entrypoint="main.py",
                keep_alive=True,
            )
            session.add(auto)
            await session.flush()
            run = AutomationRun(
                id=self.run_id,
                automation_id=auto.id,
                status=AutomationRunStatus.RUNNING,
                run_metadata={"owner": "keep"},
            )
            session.add(run)
            await session.commit()
        self.patches = [
            patch(
                "openhands.automation.router.capture_automation_event", new=AsyncMock()
            ),
            patch(
                "openhands.automation.router.record_first_run_outcome", new=AsyncMock()
            ),
            patch(
                "openhands.automation.router.maybe_disable_unhealthy_automation",
                new=AsyncMock(return_value=False),
            ),
        ]
        for item in self.patches:
            item.start()

    async def asyncTearDown(self):
        for item in self.patches:
            item.stop()
        await self.engine.dispose()
        self.tmp.cleanup()

    async def call(self, outcome, fetch=None):
        body = RunCompleteRequest(
            status="COMPLETED", conversation_id=str(uuid4()), task_outcome=outcome
        )
        async with self.sessions() as session:
            with patch(
                "openhands.automation.router.fetch_latest_finish_tool_response_for_run",
                new=fetch
                or AsyncMock(return_value={"message": "real finish", "custom": 3}),
            ):
                result = await complete_run(
                    self.run_id,
                    body,
                    Request({"type": "http", "headers": []}),
                    self.user,
                    session,
                )
                await session.commit()
                return result

    async def test_operational_success_keeps_business_blocked(self):
        result = await self.call({"status": "blocked", "outcome_summary": "scope gate"})
        self.assertEqual(result.status.value, "COMPLETED")
        self.assertEqual(result.run_metadata["owner"], "keep")
        self.assertEqual(
            result.run_metadata["finish_tool_response"]["status"], "blocked"
        )
        self.assertEqual(result.run_metadata["finish_tool_response"]["custom"], 3)

    async def test_missing_outcome_keeps_real_finish(self):
        result = await self.call(None)
        self.assertEqual(
            result.run_metadata,
            {
                "owner": "keep",
                "finish_tool_response": {"message": "real finish", "custom": 3},
            },
        )

    async def test_duplicate_completion_rejected(self):
        await self.call({"status": "success", "outcome_summary": "done"})
        with self.assertRaises(HTTPException) as raised:
            await self.call(
                {"status": "blocked", "outcome_summary": "must not overwrite"}
            )
        self.assertEqual(raised.exception.status_code, 409)

    async def test_wrong_owner_rejected(self):
        self.user = AuthenticatedUser(
            uuid4(),
            self.org_id,
            "test@example.com",
            "admin",
            ["view_automations"],
            AuthMethod.API_KEY,
        )
        with self.assertRaises(HTTPException) as raised:
            await self.call({"status": "success"})
        self.assertEqual(raised.exception.status_code, 403)

    async def test_watchdog_refresh_metadata_preserved(self):
        async def fetch(*_):
            async with self.sessions() as other:
                await other.execute(
                    update(AutomationRun)
                    .where(AutomationRun.id == self.run_id)
                    .values(
                        status=AutomationRunStatus.FAILED,
                        error_detail="Timed out: isolated test",
                        run_metadata={"owner": "keep", "watchdog": "fresh"},
                    )
                )
                await other.commit()
            return {"message": "real finish", "custom": 3}

        result = await self.call(
            {"status": "partial_success", "outcome_summary": "explicit result"}, fetch
        )
        self.assertEqual(result.status.value, "COMPLETED")
        self.assertEqual(result.run_metadata["watchdog"], "fresh")
        self.assertEqual(
            result.run_metadata["finish_tool_response"]["status"], "partial_success"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
