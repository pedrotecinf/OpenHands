# VPS deployment completed

OpenHands Canvas 1.27.1, SDK/Agent Server/tools/workspace 1.54.0, and Automation
1.19.3 were deployed from the fork after the conversation and automation idle
gates passed. `deployment-approval.json` binds the approved deployed source and
image; the original `upgrade.json` remains the pre-approval build manifest.

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
