# Forked TypeScript client

The local MCP reload endpoint is implemented in the matching
`pedrotecinf/software-agent-sdk` fork. The upstream npm client does not expose
`ConversationClient.reloadMCP` yet.

This directory carries the built npm package from that fork so `npm ci` and
Docker builds use the same typed client without editing `node_modules`.
Only the package's declared `dist` files are included by `npm pack`.
The lockfile binds the archive's integrity. See `fork/upgrade.json` for the
SDK source revision and the candidate image's upstream digest.
