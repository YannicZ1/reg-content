# Reg's Content System (Claude plugin)

For Reg's clients. Adds four skills to Claude:

- **weekly-content**: the weekly session (ideas, scripts, filming checklist, then editing)
- **content-ideas**: video ideas from your own business, across Reach, Trust and Sell
- **write-script**: one script in Reg's format and your voice, checked before you see it
- **edit-reel**: edits your filmed video into a reel with Reg's Reel Editor (best takes, captions, hook
  title, a few smart zooms, music), in your saved look; also changes that look when you ask

Setup: follow the "Your AI Setup Guide" you got from Reg's team. Needs a paid Claude plan (Pro or above)
and a Project with your content-brain.md and my-first-10-scripts.md.

## Reel Editor connector

The plugin connects to Reg's Reel Editor server (`reel-editor` in `plugins/content-system/.mcp.json`):
you upload your raw video through a link (works on a phone), Claude decides the edit from the transcript,
the server renders the reel and checks it before you see it.

Connect it once: open the plugin, go to its Connectors tab and click Connect next to Reel Editor. A window
opens for a moment and closes again, no password and no code. The connection then stays active in every chat.

## For Reg's team

Installed plugins do not update themselves, so every skill starts with a Step 0 that fetches its current text
from the Reel Editor (`get_playbook`). After editing a skill here: bump the version in `plugin.json` and
`.claude-plugin/marketplace.json`, commit, run `reel-engine/deploy/sync_playbooks.sh` and deploy reel-engine
(its `deploy/README.md`, Updates). Existing installs get the new text on their next request; push this repo
too so new installs start from it.

`evals/edit_reel_eval.py` (not part of the shipped plugin) checks that a Claude following the edit-reel
skill writes edits the renderer turns into clean reels. It needs a local reel-engine checkout and the test
clips; no clip data is kept in this repo. Run: `python3 evals/edit_reel_eval.py --out /tmp/edit-reel-eval`.
