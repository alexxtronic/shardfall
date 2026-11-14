# Start making assets

```bash
cd /Users/alexdamore/Desktop/Vibe_Code/shardfall
claude
```

This directory is configured for claude. Accept the project/MCP trust prompts. Ask the agent to read AGENTS.md and create an asset. Kiln needs no separate model key.

Core author/refine/QA skills are installed and registered for this harness. Optional compose/batch skills are selected at setup with --skills compose,batch.

These are shared CLI/MCP skills for your chosen harness. The optional built-in Strands agent adds its workflow internally; do not copy its prompt or native workflow into this workspace.

Long-running and headless sessions may compact context automatically. AGENTS.md describes the harness-neutral KILN_PROGRESS.md handoff that preserves the current programRef and next action across compaction. Harness-specific thresholds are documented in Kiln's docs/harnesses.md; leave native automatic compaction enabled when the active model's context size is unknown.

Keep assets here and engine source outside. This separates task context, not operating-system permissions. User instructions and authentication can still apply.

Run repair after anything that invalidates the generated absolute paths: moving this workspace, moving or reinstalling the runtime, or removing the Node executable that setup recorded. The manifest pins the exact interpreter the preflight check validated. Invoking the CLI with another supported Node does not require repair while the recorded executable remains available.

```bash
node /opt/homebrew/lib/node_modules/@instruktlabs/kiln/scripts/create-workspace.mjs /Users/alexdamore/Desktop/Vibe_Code/shardfall --repair
```

That path is where the installation was at setup. If the installation itself moved, run the same command from its current location; `runtime` in .kiln/workspace.json records where this workspace last expected it.

Repair updates generated runtime paths only and refuses edited configuration. For a runtime or skill update, stop the harness/MCP session, run kiln-init on this directory with --check and then --upgrade, and restart the session. Upgrade refreshes unchanged managed configuration, instructions and all skill copies; conflicting edits stop it before writing. Preserve and resolve the named files explicitly. Assets and saved revisions remain in place.
