"""Validate captured production formats offline, without starting agent runtimes."""

import argparse
import importlib
import json
import logging
from pathlib import Path

from openhands.agent_server.models import StoredConversation
from openhands.agent_server.persistence.models import PersistedSettings
from openhands.sdk.conversation.state import ConversationState
from openhands.sdk.event import Event
from openhands.sdk.tool.client_tool import ClientToolSpec, register_client_tools
from openhands.sdk.utils.cipher import Cipher


logging.disable(logging.CRITICAL)
for module in (
    "openhands.sdk.tool.builtins",
    "openhands.sdk.mcp.tool",
    "openhands.tools.glob",
    "openhands.tools.grep",
    "openhands.tools.planning_file_editor",
):
    importlib.import_module(module)
parser = argparse.ArgumentParser()
parser.add_argument("state", type=Path)
args = parser.parse_args()
root = args.state
cipher = Cipher((root / "agent-canvas/secret-key.txt").read_text().strip())
context = {"cipher": cipher}
settings = PersistedSettings.from_persisted(
    json.loads((root / "settings.json").read_text()), context=context
)
report = {
    "conversations": 0,
    "events": 0,
    "settings_valid": True,
    "encrypted_fields_verified": 0,
    "failures": [],
}


def verify_encryption(value):
    if isinstance(value, dict):
        for item in value.values():
            verify_encryption(item)
    elif isinstance(value, list):
        for item in value:
            verify_encryption(item)
    elif isinstance(value, str) and value.startswith("gAAAAA"):
        if cipher.try_decrypt_str(value) is None:
            raise ValueError("Persisted encrypted field cannot be recovered")
        report["encrypted_fields_verified"] += 1


for path in [
    root / "settings.json",
    root / "secrets.json",
    *sorted((root / "profiles").glob("*.json")),
    *sorted((root / "provider-connections").glob("*.json")),
]:
    verify_encryption(json.loads(path.read_text()))
for directory in sorted((root / "agent-canvas/conversations").iterdir()):
    if not directory.is_dir():
        continue
    try:
        stage = "metadata"
        meta = json.loads((directory / "meta.json").read_text())
        verify_encryption(meta)
        for module in meta.get("tool_module_qualnames", {}).values():
            if not module.startswith(
                ("openhands.tools.", "openhands.sdk.tool.builtins.")
            ):
                raise ValueError("Review non-stock persisted tool module before import")
            importlib.import_module(module)
        if meta.get("client_tools"):
            register_client_tools(
                [ClientToolSpec.model_validate(t) for t in meta["client_tools"]]
            )
        stored = StoredConversation.model_validate(meta, context=context)
        stage = "base_state"
        verify_encryption(json.loads((directory / "base_state.json").read_text()))
        state = ConversationState.model_validate_json(
            (directory / "base_state.json").read_text(), context=context
        )
        assert stored.id == state.id
        ids = set()
        stage = "events"
        for path in sorted((directory / "events").glob("*.json")):
            data = json.loads(path.read_text())
            if "kind" not in data:
                continue
            event = Event.model_validate(data, context=context)
            ids.add(str(event.id))
            report["events"] += 1
        if state.leaf_event_id:
            assert str(state.leaf_event_id) in ids, (
                "Leaf event not present in checkpoint"
            )
        if state.last_user_message_id:
            assert str(state.last_user_message_id) in ids, (
                "User cursor not present in checkpoint"
            )
        report["conversations"] += 1
    except Exception as error:
        failure = {
            "id": directory.name,
            "stage": stage,
            "error_type": type(error).__name__,
        }
        if hasattr(error, "errors"):
            failure["fields"] = [
                {"type": e["type"], "loc": e["loc"]}
                for e in error.errors(
                    include_input=False, include_context=False, include_url=False
                )
            ]
        report["failures"].append(failure)
print(json.dumps(report))
if report["failures"]:
    raise SystemExit(1)
