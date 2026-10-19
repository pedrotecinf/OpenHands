# VPS deployment completed

## Current deployment: Canvas 1.28.0 (2026-10-19)

- Canvas source: `b2679662646dccbfe73491898fd2bd198537ed60`.
- SDK source: `ff5eed627cfaf4c7498ba4660bf712d6eb9293ee`.
- SDK/Agent Server/tools/workspace: 1.55.1; Automation: 1.21.0.
- Image: `openhands-canvas:fork-1.28.0-b2679662646d`.
- Image ID: `sha256:884025c56cee613fcc473cc9fe8a8efc2dc2b883df56019c36f4896e5b367f85`.
- Consistent backup: `/opt/openhands-backups/canvas128-cutover-20261019T165137Z`.
- Evidence directory:
  `/opt/openhands-canvas/fork-candidates/b2679662646dccbfe73491898fd2bd198537ed60`.

Before/after snapshots match exactly: 54 conversations, 31,805 event file
hashes, execution states, leaf/user/ACP cursors, provider session identities,
and authentication/encryption key hashes. Offline parsing recovered 822
encrypted fields. A pre-existing directory containing only `.owner_lease.lock`
is reported separately; it contains no conversation metadata or events and
was not removed. Four profiles, nine MCP definitions, the active profile,
17 historical automation runs, and the one enabled automation remain present.
SQLite integrity, web HTML, and frontend asset requests passed after cutover.

The isolated Claude canary executed terminal and MCP tools, then recalled its
token and executed another command with the same provider session ID after
the container was recreated. The native MCP reload smoke also passed after
recreation. Local suites passed 1,128 tests; callback tests passed seven with
one optional deployed-module parity test skipped. No production conversation
was resumed for this maintenance. PIL-86 received the maintenance-complete
notice through the existing coordination flow.

For rollback, first preserve any post-cutover events and stop active work.
Restore the backup's matching state and Compose together; the projects archive
is available if needed. Do not run the old image against migrated state as an
unverified shortcut. Private container inspection is stored only in the backup.

## Previous deployment: Canvas 1.27.1 (2026-10-13)

OpenHands Canvas 1.27.1, SDK/Agent Server/tools/workspace 1.54.0, and Automation
1.19.3 were deployed from the fork after the conversation and automation idle
gates passed. The 1.27.1 approval and pre-approval build manifest remain in Git
history; the files in this checkout now describe the 1.28 deployment.

The final stopped-state backup is
`/opt/openhands-backups/fork-cutover-20261013T025248Z`. It includes original
Compose, rollback Compose, private container inspection, state/projects,
temporary worktrees, and before/after conversation proof. Both gzip archives
passed integrity checks, and rollback Compose passed configuration validation.

All 31 conversations retained exactly the same event IDs, execution statuses,
leaf IDs, user cursors, ACP cursors, and provider session IDs after startup.
Authentication/encryption key-file hashes remained unchanged. No stopped
conversation was resumed for verification. The GitHub identity is Bot-openhands.

Temporary worktrees now persist at
`/opt/openhands-canvas/projects/.conversation-worktrees-20261013T025248Z`, mounted
at the original `/tmp/conversation-worktrees` path. Docker copy initially gave
these files root ownership. The preflight archive proved every original member
used UID/GID 10001:10001; that ownership was restored, and native-user Git
readback confirmed the active worktree is accessible. The rollback worktree
archive also carries corrected ownership without altering its file payloads.

The two old Automation 1.19.0 overlay mounts were replaced by narrow, tested
patches baked into the 1.19.3 image. Existing state, Claude HOME, workspace,
project mounts, bot configuration, and environment remain in place.

The panel returned HTTP 200 from both Mac and Windows tunnels. Browser readback
confirmed the conversation list, Portuguese UI, Claude cc-opus selection, and
new Code/Automate splash toggle. The new container is healthy.

Coordinate credential rotation for the process-argument diagnostic exposure
separately. Never publish private backup files or print complete process arguments.
