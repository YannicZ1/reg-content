---
name: edit-reel
description: Edit the user's filmed talking-head video into a finished Instagram Reel with Submagic (captions, hook title, zooms, cut pauses and bad takes, b-roll) in their saved template. Use when the user says "edit my reel", "edit my video", "I filmed it", "make this a reel", or wants a change to a reel Submagic already edited.
---

# Edit a reel with Submagic

The owner films, you get the video edited. Submagic does the editing through its connector (tools such as
`create_upload_link`, `list_iris_templates`, `start_iris_edit`, `ask_iris`). Claude cannot watch video, so
never describe what is in the video. Describe only what you asked Submagic to do and what it returned.

## 0. Is Submagic connected?

If you have no Submagic tools in this chat, stop and say exactly:
"Turn on Submagic for this chat: click + under the message box, then Connectors, then switch Submagic on.
If you do not see it, open your setup guide, Part 4."

## 1. Which script is this video?

Ask once, unless they already said: "Which script did you film? Paste the hook or the title."
Find it in this chat or in my-first-10-scripts.md. From it you take:
- the lane: Reach (TOFU), Trust (MOFU) or Sell (BOFU),
- the on-screen hook title: the first beat of the hook, at most 8 words, in capitals
  (from "TWO ROOFING QUOTES CAN LOOK THE SAME ON PAPER. ONLY ONE OF THEM IS STILL THERE AFTER THE STORM."
  take "TWO QUOTES. ONLY ONE SURVIVES THE STORM." or "TWO ROOFING QUOTES CAN LOOK THE SAME"),
- for a Sell script: the comment keyword.
If they skip it, edit without a hook title and say so.

## 2. Pick the template

List their templates (`list_iris_templates`). Use the one named **Reg Style** unless they name another one.
If they also have **My Style**, ask once which one, and remember the answer for this chat.
If there is no Reg Style template, say: "Your Reg Style template is missing. Open your setup guide, Part 4,
step 3, then come back." Do not edit without a template unless they ask you to.

## 3. Get the video

Create an upload link (`create_upload_link`) and send it with one line:
"Open this link, pick your video and send it. It works from your phone. Start the upload within 30 minutes."
Videos must be under 3 minutes.

## 4. Start the edit

Start one edit (`start_iris_edit`) with their template and this brief, filled in for the lane:

- All lanes: "Captions on. Cut every silence and every repeated or broken take, keep the best take of each
  line. Put the hook title [HOOK TITLE] on screen in the first 3 seconds. Keep the speaker's face in frame.
  No emojis, no meme sound effects. Clean and calm."
- Reach (TOFU): "Zoom in on the strongest lines, about every 5 to 8 seconds. B-roll only where it shows the
  concrete thing being said, about a quarter of the video. Fast pace."
- Trust (MOFU): "Few zooms, only on the key sentence and the climax. Little b-roll, only where it shows the
  thing being explained. Steady pace, let the sentences land."
- Sell (BOFU): "Almost no b-roll, the face carries it. Zoom on the numbers and on the last line. In the last
  4 seconds show 'Comment [KEYWORD]' big in the center."

Then tell them: "Your edit is running. It takes about 11 to 20 minutes. I will show it here when it is done."

## 5. Deliver and fix

- When it is done, show the result and the Submagic link.
- Small changes go through the same edit (`ask_iris` with the change in plain words), not a new edit.
  Every new edit costs credits, a change inside the edit does not use a new edit.
- Then: "Happy with it? Open the link, click Export (top right), then Download, and post it."

## If something goes wrong

Never start the same edit twice. If a call fails or takes longer than 25 minutes, ask Submagic for the
status of their projects first and continue from there. If Submagic says they are out of credits, say so in
one line and point them to their Submagic plan page. Do not guess.
