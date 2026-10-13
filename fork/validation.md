# Candidate validation evidence

## Immutable source bindings

- Canvas tested code revision: `149c7d3133b8aaa252f70dd3813ec4a02d205354`.
- SDK revision: `9f850bf8b3f7a785d5d833dd1e3af1c31f96028d`.
- Releases: Canvas 1.27.1, SDK/Agent Server 1.54.0, Automation 1.19.3.
- Base image and client archive integrity: see `upgrade.json`.
- Final local amd64 image index:
  `sha256:be443f34394ed1c12ac1323beb915a013f9079a2f51b885081e9cec15ac8d6ee`.

The image was built locally, not published to a registry. The documentation
commit carrying this report is subsequent to the tested code revision above.

## Automated checks

| Check | Result |
| --- | --- |
| MCP reload, ACP agent, and Codex session persistence | 501 Python tests passed |
| EventService regression suite | 118 Python tests passed |
| TypeScript client unit suite | 384 tests passed |
| Canvas adapter, creation, reload UI, and direct-call guard | 185 tests passed |
| Version-sync and Docker import checks | 41 tests passed |
| Compatibility floor, prerelease, and version-sync checks | 86 tests passed |
| Canvas typecheck, lint, translations, and static build | Passed |
| SDK Ruff, Pyright, import/tool/dynamic-attribute commit gates | Passed |
| Deterministic OpenAPI export, type-quality, and Swagger validation | Passed |

The counts are per invocation; overlapping suites are not additive. The reload
route was strengthened to a named response model after the OpenAPI gate rejected
an unrestricted dictionary. Its updated HTTP tests passed again.

## Real isolated container checks

Built and exercised Linux arm64 and Linux amd64 images on Docker Desktop.
The amd64 check runs under emulation on the Mac, not on the production VPS.

- Web listener returned HTTP 200 and both services became healthy.
- A real stdio FastMCP process exposed `fork_marker` after API reload.
- Browser menu action returned “MCP configuration reloaded. Conversation
  preserved. Servers: forkprobe”.
- Native conversation `7b87eeb9-5400-4b5e-8456-615206b7d753` retained all four
  event IDs and the `FORK_HISTORY_PRESERVED` message after cold restart.
- Replacing the test container with the final image and the same stopped-canary
  volumes retained the same conversation and message IDs and reloaded the MCP.
- No paid LLM requests or production credentials were used.

The canary has no configured LLM account, so the UI correctly requests LLM
setup. This check does not establish Claude/Codex provider authentication or
cold resume on the new image. Those checks and the deployed automation override
review remain required by `README.md` before production approval.

## Promotion state

**Candidate prepared; production approval pending.** The production VPS was not
updated, restarted, or used for these builds and tests. Preserve full state,
provider sessions, bot configuration, and workspace files before any later
idle-window deployment.
