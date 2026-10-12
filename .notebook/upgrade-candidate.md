# Upgrade candidate

- `fork/upgrade.json` owns the immutable upstream-image and SDK-source bindings.
- `scripts/build-fork-image.mjs` builds `docker/Dockerfile.fork` with those bindings.
- `fork/patch_claude_resume.py:patch_module()` carries the deployed alias fix
  without vendoring or overwriting the complete upstream wrapper.
- `vendor/` owns the built TypeScript client; npm lockfile integrity binds it.
- `agent-server-adapter.ts:buildStartPlanningConversationRequestWithEncryptedSettings()`
  selects a saved compatible LLM for ACP-parent planners and preserves encryption.
- `fork/README.md` documents isolated checks and the remaining promotion criteria.
- Production was not updated or restarted during candidate preparation.
