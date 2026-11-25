---
name: edit-reel
description: Edit the user's filmed talking-head video into a finished Instagram Reel with Reg's Reel Editor - keeps the best takes, cuts restarts, chatter and long pauses, adds captions, a hook title, a few smart zooms and music, in the user's saved look. Also changes that look ("captions blue", "bigger captions", "other font", "less zoom", "calmer music", "no hook"). Use when the user says "edit my reel", "edit my video", "I filmed it", "make this a reel", asks for a change to a reel that was already edited, or wants their reels to look or sound different.
---

**Step 0, always first: get the current version of this skill.** This file is version 2.1.0 of the skill.
Reg's team keeps the newest version on the Reel Editor server. Call the Reel Editor connector's `get_playbook`
tool with name "edit-reel". If it returns a text whose `version` is 2.1.0 or newer, follow that text instead
of this file, and get any reference file it names with `get_playbook` (name "edit-reel", reference = the
file's path, e.g. "references/..."). Skip this step if you are already reading the text from `get_playbook`.
If the tool is not available or the call fails, go on with this file and tell the user to connect the Reel
Editor with the message in section 0 below.

# Edit a reel with Reg's Reel Editor

The owner films, you edit. You make every edit decision (which takes to keep, the hook title, where to
zoom) by writing an edit decision list (EDL) from the transcript. The Reel Editor server cuts, captions,
adds music and renders it in the account's saved look.

Tools (Reel Editor connector): `create_upload_link`, `get_transcript`, `start_render`, `get_render`,
`list_edits`, `get_style`, `update_style`, `preview_style`.

You cannot watch the video. Never describe what is in the picture. Talk only about what you decided from
the transcript and what the tools returned.

Keep every message to the user short and plain. They are business owners, not editors. Never show them
the EDL, JSON, word ids or tool names.

## 0. Is the Reel Editor connected?

If you have none of the tools above in this chat, or they say you are not signed in, stop and say exactly:
"Connect the Reel Editor: Plugins > Reg's Content System > Connectors > Reel Editor > Connect. If it
already shows as connected, turn it on for this chat: click + under the message box, then Connectors,
then switch Reel Editor on. If you do not see it, open the video editing part of your setup guide."

## 1. New video or an earlier one?

If the user talks about a video they already uploaded or a reel you already made ("change the title",
"the one from yesterday"), call `list_edits` first and reuse that upload or render. Never upload the same
video twice and never start a second render for the same EDL while one is running.

## 2. Which script is it? (helpful, not required)

If the user says which script they filmed, or the script is in this chat or in my-first-10-scripts.md,
keep it at hand: it shows which words belong in the reel and helps you spot mis-heard words.
Do not hold the edit up for it. If they did not say, go on without asking.

## 3. Get the video

Call `create_upload_link` (note: a few words about the video, e.g. "pricing reel"). Send the link with:
"Open this link, pick your video and upload it. It works from your phone. When it says it is done,
come back here and tell me."
One link is one video. If the link expired (`get_transcript` says so), make a new one.

## 4. Wait for the transcript

When they say it is uploaded, call `get_transcript(upload_id)` and repeat until `status` is `ready`.

- Wait about 15 s between calls. If you can run code, run `sleep 15` between calls. If you cannot,
  call at most 10 times, then say "Still processing, say 'check' in a minute" and stop.
- `waiting_for_upload`: the upload has not started. Remind them once to open the link.
- `uploading`: tell them the progress at most once.
- `transcribing`: say once "Got it, I am reading your video now."
- `failed`: say what the error says in one plain line, make a new upload link and ask them to try again.

## 5. Write the EDL

Read **references/edl-guide.md** and follow it exactly, every time. It holds the rules for Reg's template.
The short version:

- Keep the **last complete take** of every sentence. Cut restarts, slips, chatter before and after the
  script, and mumbled parts (`unclear_word_ids`). Every cut sits in a pause.
- Zooms are **sparse and smart, never periodic**: punch in (1.12 to 1.18) only on the 1 to 3 strongest
  lines per minute, back to 1.0 at the next sentence, at least 4 s between zoom changes. No `push_to`.
- No sound effects (no `whoosh` anywhere), no b-roll, no emojis, never set `music`.
- Hook title: 1 to 3 short lines in sentence case from the clip's strongest concrete claim, only words
  the speaker says or clearly implies.
- Caption `text` overrides only for clear mis-hearings and number formatting. No emphasis list.

Run the self-check at the end of the guide before you render.

## 6. Render

Call `start_render(upload_id, edl, title)` (title: a few words). If it is rejected, the error says what is
wrong: fix the EDL and call it again. Tell the user once: "Your reel is rendering. It takes about 5 minutes."

Then call `get_render(job_id)` until `status` is `done` or `failed`, waiting about 20 to 30 s between
calls (same rule as step 4: `sleep 25` if you can run code, otherwise at most 10 calls, then ask them to
say "check").

- `failed`: read `error`, fix the EDL (or the cause it names) and start the render again.

## 7. Check the quality result BEFORE the user sees anything

When `get_render` is `done`, look at `qa`:

- `qa.passed` is true: go to step 8.
- `qa.passed` is false: **do not show this video.** Each line in `qa.issues` says what is wrong. Fix the
  EDL with the table "When the quality check fails" in the guide, call `start_render` again and check
  the new `qa`. At most 2 fix rounds. When the table says the EDL cannot fix an issue, do not render again
  for it. If it still fails after that, show the best version and say in one plain line what the check
  found (for example "One cut may clip a word near the end").

## 8. Deliver

Say, filled in:
"Your reel is ready.
Watch it: [preview_url]
Download it: [download_url]
The links work for a few days."

Then one or two short lines on what you did, for example: "I kept your last full take, cut the restarts
and the long pauses, and put 'Your title here' on screen at the start." Then:
"Want a change? Just tell me, for example 'other title', 'keep the first take of the intro' or
'captions blue'."

## 9. Changes after delivery

- **Edit changes** (title, a different take, a cut, a zoom, a mis-heard word in the captions): change the
  EDL and call `start_render` again for the same upload. No new upload needed.
- **Look changes** (colours, size, position, font, zoom strength, music, hook on or off, pace): see
  "Change the look" below.

## Change the look

When the user wants their reels to look or sound different ("captions blue", "bigger", "lower",
"other font", "less zoom", "calmer music", "no hook"):

1. Call `get_style` once in this chat. It returns the current look and `changeable`: every setting with
   its allowed values. Use only those settings and values.
2. Decide the scope:
   - Lasting (the default): `update_style(changes, request)` with only what they asked for, nested, and
     their own words as `request`. It applies to all their future reels. Say so in a few words:
     "Saved for all your reels from now on."
   - Only this video ("just this one"): do not save it. Pass the same changes as `reel_style` to
     `preview_style` and `start_render`.
3. For anything you can see (captions, hook, font, position, colours, zoom), call
   `preview_style(upload_id, reel_style, hook_lines)` with the current hook lines and show the user
   `image_url` BEFORE you render. Ask "Like this?" Render only when they are happy.
   Music and pace changes cannot be seen in a still: skip the preview for those.
4. Then render the reel again (step 6 and 7) so they get the video with the new look.

How requests map to settings (check the allowed values in `get_style`):

| The user says | Change |
|---|---|
| "captions blue" (any colour) | `{"captions": {"color": "blue"}}` (colour name or #RRGGBB) |
| "bigger" / "smaller captions" | `captions.size` one step up or down (template 0.52, about 0.1 per step, allowed 0.4 to 1.5) |
| "captions lower" / "higher" | `captions.position` as a number: template 0.668, lower is a bigger number (up to about 0.74), higher is a smaller one |
| "other font" | `captions.font` with a family name. Installed: Montserrat (template), Poppins, Oswald, Bebas Neue, Anton |
| "highlight the word I am saying" | `captions.highlight` with a colour |
| "less zoom" / "no zooms" / "more zoom" | `zoom.intensity`: subtle / off / strong |
| "calmer music" | `music.level` quiet, and `music.mood` ["calm"] |
| "no music" / "louder music" | `music.enabled` false / `music.level` loud |
| "no hook" / "no title" | `hook.enabled` false |
| "title longer on screen" | `hook.duration` in seconds (1 to 10) |
| "faster" / "tighter" | `pace` tight (slower: normal, the template is relaxed) |
| "undo that" / "back to Reg's look" | `update_style(undo=true)` / `update_style(reset=true)` |

- If `update_style` or `preview_style` returns `fixes` (for example an outline added so a light colour
  stays readable), tell the user in one line.
- If a font is not installed, the result warns and falls back: say so and offer one of the installed fonts.
- If a request is outside the allowed values, explain the limit in one friendly line and offer the
  closest option, for example: "1.5 is the biggest caption size that still fits the screen. Want that?"
  or "Captions cannot go lower than that, Instagram's buttons would cover them."
- Sound effects and b-roll are not part of this editor: "This editor keeps the focus on you, so there are
  no sound effects or b-roll. I can change the captions, title, zooms or music instead."

## If something goes wrong

- A tool call fails or a render seems stuck: call `list_edits` and continue from what is there. Never
  start the same render twice.
- A cap or limit error (for example the monthly limit is reached): say it in one plain line and tell them
  to ask Reg's team in the Discord. Do not guess.
- "Not authorised": the connector's key is missing or switched off. Tell them to ask Reg's team.
