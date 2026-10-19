"""Apply only the deployed callback metadata behavior to Automation 1.21.0."""

import argparse
import hashlib
from pathlib import Path


UPSTREAM_SHA256 = "66ac72cd170b847317978c7ff2f699cc5782db2c0e13e7a4014fa6de2cdbec23"
IMPORT = (
    "from openhands.automation.utils.callback_metadata import merge_callback_metadata\n"
)
IMPORT_ANCHOR = (
    "from openhands.automation.utils.callback_error import format_callback_error\n"
)
OLD_METADATA = """    if body.conversation_id:
        finish_tool_response = await fetch_latest_finish_tool_response_for_run(
            run, body.conversation_id
        )
        if finish_tool_response is not None:
            values["run_metadata"] = {
                **(run.run_metadata or {}),
                "finish_tool_response": finish_tool_response,
            }
"""
NEW_METADATA = """    finish_tool_response = None
    if body.conversation_id:
        finish_tool_response = await fetch_latest_finish_tool_response_for_run(
            run, body.conversation_id
        )
    if body.task_outcome is not None or finish_tool_response is not None:
        values["run_metadata"] = merge_callback_metadata(
            run.run_metadata, body.task_outcome, finish_tool_response
        )
"""
OLD_RECONCILE = """            values["error_detail"] = None
            reconcile_stmt = (
"""
NEW_RECONCILE = """            values["error_detail"] = None
            if "run_metadata" in values:
                # Preserve any watchdog metadata observed by refresh above.
                values["run_metadata"] = merge_callback_metadata(
                    run.run_metadata, body.task_outcome, finish_tool_response
                )
            reconcile_stmt = (
"""


def patch_router(router: Path, metadata_source: Path) -> None:
    text = router.read_text()
    original = (
        text.replace(IMPORT, "", 1)
        .replace(NEW_METADATA, OLD_METADATA, 1)
        .replace(NEW_RECONCILE, OLD_RECONCILE, 1)
    )
    if hashlib.sha256(original.encode()).hexdigest() != UPSTREAM_SHA256:
        raise ValueError("Automation router differs from the verified 1.19.3 source")
    if text == original:
        for anchor in (IMPORT_ANCHOR, OLD_METADATA, OLD_RECONCILE):
            if original.count(anchor) != 1:
                raise ValueError("Automation callback insertion point is not unique")
        text = original.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + IMPORT, 1)
        text = text.replace(OLD_METADATA, NEW_METADATA, 1)
        router.write_text(text.replace(OLD_RECONCILE, NEW_RECONCILE, 1))
    target = router.parent / "utils/callback_metadata.py"
    content = metadata_source.read_bytes()
    if target.exists() and target.read_bytes() != content:
        raise ValueError("Refusing to overwrite an unrelated callback metadata module")
    target.write_bytes(content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("router", type=Path)
    parser.add_argument("metadata_source", type=Path)
    args = parser.parse_args()
    patch_router(args.router, args.metadata_source)
