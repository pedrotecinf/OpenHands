# Final homologation

## Passing checks

- Codex `gpt-5.6-sol`: real MCP invocation, original context, and unchanged
  provider session after reload and cold restart.
- Claude `cc-opus`: the same checks passed. The test permits
  `WaitForMcpServers`, because Claude connects MCPs asynchronously.
- Codex uses a separately authorized device login, not the production OAuth
  refresh family. Claude uses isolated session storage and the static gateway
  credential, without changing production authentication state.
- Automation 1.19.3: deployed outcome metadata behavior ported as narrow,
  checksum-guarded changes. Eight isolated tests pass, including real disposable
  SQLite ORM, watchdog concurrency, permissions, redaction, and deployed parity.
- Restore checkpoint: 382,790 regular files match their archive hashes; SQLite
  integrity passes. The candidate SDK loads 31 conversations and 6,710 events,
  preserves leaf/user-message cursors, and decrypts 553 fields without failures.

The checkpoint was captured while a conversation ran. Thirty-eight state files
changed during capture, so it is qualification evidence, not a cutover backup.
Private archives and credential files remain outside these repositories.

## Cutover requirements

1. Build and verify the immutable candidate image before stopping production.
   The artifact Dockerfile accepts a locally built, hash-bound frontend so the
   VPS does not need to compile Node packages while serving users.
2. Check all conversation and automation statuses immediately before cutover.
   Do not cancel work to make this gate pass.
3. Stop the old container with at least 120 seconds grace. Capture a fresh
   consistent state/projects/Compose backup and the stopped container's temporary
   worktrees. Preserve the old image ID and all encryption identities.
4. Persist `/tmp/conversation-worktrees` with a bind mount at the same container
   path. Preserve Git worktree pointers and numeric ownership.
5. Remove only the two old automation overlay mounts, since the new image carries
   the adapted behavior. Preserve the existing state, Claude HOME, projects,
   default workspace, GitHub bot configuration, and environment.
6. Start the candidate, require both web/backend health, and compare IDs,
   event counts, execution statuses, provider session IDs, and cursor bindings.
   Readback must not resume stopped conversations or replay old requests.
7. On failure, restore the old Compose/image together with the matching backup,
   accounting for post-cutover events before overwriting state.

Credential rotation following a diagnostic process-argument exposure must be
coordinated separately; do not print process arguments or credential values.
