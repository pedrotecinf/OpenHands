# OpenHands 1.27.1 fork candidate

This branch combines Canvas 1.27.1 with the patched SDK/Agent Server 1.54.0.
`upgrade.json` binds the official base-image digest, SDK commit, and client
archive. `productionApproved` remains false until the deployment checks pass.

## Preserved behavior

- Conversation-scoped MCP reload with busy-run rejection and profile filtering.
- Strict ACP resume, Codex session-only persistence, and literal Claude aliases.
- Explicit native-agent selection and authenticated Claude planning profiles.
- Upstream 1.27.1 Docker bridge fixes and SDK 1.54 typed ACP/atomic-save changes.

The client is packaged in `vendor/` so clean installs use its typed reload API.
The Claude adapter patch verifies the exact upstream 0.63.0 module before
modifying it. Python packages come from the immutable SDK fork commit; the
Python launcher prevents the old frozen executable from hiding source changes.

## Build and isolated smoke

Use Node 24 and Docker. From this checkout:

```sh
npm ci
node scripts/build-fork-image.mjs
docker run -d --name openhands-fork-canary --memory=3g \
  -p 127.0.0.1:13800:8000 -e OPENHANDS_FORK_CANARY=1 \
  pedrotecinf/openhands-canvas:1.27.1-fork
# Wait for container health to become healthy.
docker exec openhands-fork-canary python /opt/agent-canvas/fork/smoke_canary.py
docker restart openhands-fork-canary
# Wait for health again, then verify persisted history and reconnection.
docker exec openhands-fork-canary python /opt/agent-canvas/fork/smoke_canary.py --resume
```

The smoke uses an empty canary state and no paid LLM calls. It discovers a real
stdio MCP, preserves message IDs, and checks native persistence after restart.
Never mount the production state or user projects into this canary.

## Deployment acceptance still required

Before promotion, verify Claude/Codex cold resume with dedicated test credentials,
review the two deployed automation activity overrides against Automation 1.19.3,
and restore a consistent copy of persisted state into an isolated environment.
Preserve encryption identity, provider session files, GitHub bot configuration,
workspace files, and historical message cursors. Inventory temporary worktrees
as well as persistent volumes. Schedule cutover only when production work is idle,
with a paired image-and-state backup for rollback.
