"""Exercise the fork's real HTTP/MCP path in an explicitly isolated container."""

import importlib.metadata
import json
import os
import pathlib
import sys
import urllib.request


if os.environ.get("OPENHANDS_FORK_CANARY") != "1":
    raise RuntimeError("This smoke test may only run in the isolated fork canary")

key = (
    pathlib.Path.home()
    .joinpath(".openhands/agent-canvas/api-key.txt")
    .read_text()
    .strip()
)
proof_file = pathlib.Path("/tmp/openhands-fork-native-smoke.json")
PROBE_SCRIPT = """from fastmcp import FastMCP
m = FastMCP('fork-probe')
@m.tool()
def fork_marker() -> str:
    return 'FORK_MCP_OK'
m.run(transport='stdio')
"""


def api(path, payload=None, method=None):
    headers = {"X-Session-API-Key": key}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        "http://127.0.0.1:8000" + path, data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


if "--resume" in sys.argv:
    proof = json.loads(proof_file.read_text())
    cid = proof["conversation_id"]
    events = api(f"/api/conversations/{cid}/events/search?limit=100")["items"]
    assert set(proof["event_ids"]) <= {event["id"] for event in events}
else:
    assert not api("/api/conversations/search?limit=1")["items"], (
        "Canary must start empty"
    )
    created = api(
        "/api/conversations",
        {
            "workspace": {"working_dir": "/projects/fork-smoke"},
            "agent": {
                "kind": "Agent",
                "llm": {
                    "model": "anthropic/claude-sonnet-4-20250514",
                    "api_key": "unused-canary-key",
                },
                "tools": [],
            },
            "autotitle": False,
            "worktree": False,
        },
        "POST",
    )
    cid = created["id"]
    api(
        f"/api/conversations/{cid}/events",
        {
            "role": "user",
            "content": [{"type": "text", "text": "FORK_HISTORY_PRESERVED"}],
            "run": False,
        },
        "POST",
    )
    events = api(f"/api/conversations/{cid}/events/search?limit=100")["items"]
    proof = {"conversation_id": cid, "event_ids": [event["id"] for event in events]}
    api(
        "/api/settings",
        {
            "agent_settings_diff": {
                "mcp_config": {
                    "forkprobe": {
                        "transport": "stdio",
                        "command": "python",
                        "args": ["-c", PROBE_SCRIPT],
                    }
                }
            }
        },
        "PATCH",
    )

before = api(f"/api/conversations/{cid}/events/search?limit=100")["items"]
result = api(f"/api/conversations/{cid}/reload_mcp", {}, "POST")
after = api(f"/api/conversations/{cid}/events/search?limit=100")["items"]
assert result["servers"] == ["forkprobe"]
assert any("fork_marker" in tool for tool in result["tools"]), result
assert {event["id"] for event in before} <= {event["id"] for event in after}
assert [event["id"] for event in before if event["kind"] == "MessageEvent"] == [
    event["id"] for event in after if event["kind"] == "MessageEvent"
]
proof.update(
    {
        "event_ids": [event["id"] for event in after],
        "reload": result,
        "cold_restart": "--resume" in sys.argv,
        "sdk_version": importlib.metadata.version("openhands-sdk"),
    }
)
proof_file.write_text(json.dumps(proof))
print(json.dumps(proof))
