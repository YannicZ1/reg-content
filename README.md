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

Status: the URL `https://edit.monetize-me.io/mcp` is a placeholder until the server and that domain are
live. Until then the Reel Editor tools do not connect.

## For Reg's team

`evals/edit_reel_eval.py` (not part of the shipped plugin) checks that a Claude following the edit-reel
skill writes edits the renderer turns into clean reels. It needs a local reel-engine checkout and the test
clips; no clip data is kept in this repo. Run: `python3 evals/edit_reel_eval.py --out /tmp/edit-reel-eval`.
