# Writing the EDL for Reg's template

The EDL (edit decision list) is one JSON object. It says which words to keep, the hook title, where to
zoom and which caption words to correct. It refers to the word ids from `get_transcript`. The server
does the rest (cut points in the measured silence, captions, look, music, loudness).

These rules are decided. Follow them exactly.

## What get_transcript gives you

- `words`: `[id, text, start_s, end_s]` for every spoken word, in order.
- `words_fingerprint`: copy it into the EDL unchanged.
- `unclear_word_ids`: words the transcriber was unsure of (mumbled, off-script or mis-heard).
- `stats.pauses_over_0_6s`: every pause of 0.6 s or more (`after_id` = the word before it).
- `stats.repeated_phrases`: phrases said more than once (`occurrences` as id ranges). A repeat almost
  always means a retake.

## The EDL shape

```json
{
  "version": 2,
  "words_fingerprint": "copy from get_transcript",
  "keep": [[11, 44], [53, 67]],
  "hook": {"lines": ["Two roofing quotes,", "only one is still there", "after the storm"]},
  "zoom": [{"at": 30, "scale": 1.15}, {"at": 53, "scale": 1.0}],
  "text": {"35": "FLASHING"},
  "meta": {"notes": "one line per decision: which take and why, what was cut"}
}
```

Only these keys. Never write `whoosh`, `broll`, `music`, `sfx`, `captions`, `pauses.max`, `style`,
`output` or `push_to`. The account's saved look sets captions, music, pace and colours.

## Step 1: Build your edit view

Go through `words` and start a new line wherever the gap between one word's `end_s` and the next word's
`start_s` is 0.3 s or more. Note each line's id range and the pause before it, like this:

```
[  0-4  ]  0.80- 2.10 (+0.80s) Okay, is it on? Good.
[  5-10 ]  3.40- 5.20 (+1.30s) Two roofing quotes can look the
[ 11-19 ]  6.30- 8.90 (+1.10s) Two roofing quotes can look the same on paper.
[ 20-29 ]  9.40-12.10 (+0.50s) Only one of them is still there after the storm.
[ 30-44 ] 12.60-17.80 (+0.50s) The cheap one skips the flushing, the metal strip at every edge of the roof,
[ 45-50 ] 18.20-20.00 (+0.40s) and water waits at the edges.
[ 51-52 ] 20.90-21.30 (+0.90s) No, wait.
[ 53-58 ] 22.40-24.10 (+1.10s) Water always waits at the edges.
[ 59-67 ] 24.60-27.20 (+0.50s) Ask your roofer one question: what about the flashing?
[ 68-69 ] 28.90-29.50 (+1.70s) Okay, done.
```

(This example is made up. It is used through the whole guide.)

## Step 2: Pick the takes

**Keep the last complete take of every sentence.** Complete means the sentence runs to its end without
breaking off, a slip or a restart. Cut everything else:

- **Restarts and broken takes**: a sentence that starts again ("Two roofing quotes can look the" then
  "Two roofing quotes can look the same on paper"). `repeated_phrases` points you to them. Keep the last
  one that is complete. In the example: cut 5-10, keep 11-19.
- **Slips**: a broken word, a wrong word the speaker then corrects ("We fix-- We finish every job"): cut
  the slip and keep the corrected words.
- **A sentence said twice in different words**: the later complete version is the take ("and water waits
  at the edges" ... "No, wait." ... "Water always waits at the edges"): cut 45-52, keep 53-58.
- **Off-script chatter** before the script, between takes and after it: "is it on?", "okay, one more
  time", "wait, let me start over", talk about the room, the phone, the camera, "okay, done". The reel
  starts at the first word of the script and ends with its last word. In the example: cut 0-4 and 68-69.
- **Mumbled parts**: a stretch where most words are in `unclear_word_ids` (2 or more unclear words close
  together, or unclear words in chatter). Cut it. A single unclear word inside a clean sentence you keep
  is normal: keep it. Never cut one word out of the middle of a sentence.

Nothing else is cut. Inside the read, everything the speaker says clearly stays, even when it is not a
full sentence: asides, fillers and the speaker's own style ("listen", "look", "right?", "here's the thing",
"honestly", a short half-sentence they never repeat). Those are their voice, not chatter. Cut a part of the read only
when it is a restart, a slip or mumbled. If you are unsure, keep it.

If the whole script was read more than once, the last full run is usually the take. Still check each
sentence in it: if a sentence in the last run is broken and an earlier one is complete, keep that one.
When the user told you which script it is, use it to tell the script from chatter.

## Step 3: Place every cut in a pause

- The first word of every `keep` range must have a pause of at least 0.25 s before it, and the last word
  must have a pause of at least 0.25 s after it (gap = next `start_s` minus previous `end_s`). Bigger is
  better: prefer the biggest pause near the place you want to cut.
- If the take you want starts or ends in the middle of a phrase, move the boundary to the nearest pause,
  even if that keeps or drops one extra word of chatter. Never start or end a range between two words
  with no gap.
- `keep` ranges ascend and never overlap. Both ids are included.
- Do not make extra ranges just to remove pauses inside a take: the server shortens long pauses by itself.

In the example: `"keep": [[11, 44], [53, 67]]`. Read the kept text once from start to end: every sentence
appears exactly once, complete, in order, with no chatter.

## Step 4: The hook title

The server shows it in a box for the first seconds of the reel.

- 1 to 3 short lines, each at most about 24 characters, at most about 10 words in total.
- Sentence case: a capital first letter, the rest as you would write it normally. Not ALL CAPS.
- Take it from the clip's **strongest concrete claim**: the surprising fact, the number, the turn.
- Use only words the speaker actually says or clearly implies. You may shorten, drop filler words and
  write numbers as digits ("two hundred fifty thousand" becomes 250,000). Do not add a claim, a
  promise or a number that is not in the clip. No clickbait the clip does not pay off.
- No emojis, no hashtags, no quote marks.

Example: `["Two roofing quotes,", "only one is still there", "after the storm"]`.

## Step 5: Zooms - sparse and smart, never periodic

The reel stays wide (1.0) most of the time. A zoom is a punch-in that marks a line as important.
Regular in and out zooming looks nervous and cheap: never zoom on a rhythm.

- **How many**: punch in only on the **1 to 3 strongest lines per minute** of the finished reel. Count
  the minutes of kept speech: a 30 s reel gets 1 (at most 2), a 60 s reel 1 to 3, a 90 s reel at most 4.
  Fewer is fine. Zero is fine for a very short reel.
- **Which lines**: the key claim, a number, the punchline. Not filler, not the setup.
- **Punch in**: `{"at": <first word of that line>, "scale": 1.15}`. Use 1.12 to 1.18 only (1.18 for the
  single biggest moment).
- **Back out**: `{"at": <first word of the next sentence>, "scale": 1.0}`, or of a later sentence when the
  next one comes too soon (see the 4 s rule below).
- **Hide a jump cut**: if a take cut sits right at a strong line or at the start of the next sentence,
  put the zoom change exactly on the first word after the cut (the first id of that `keep` range). The
  change then lands on the cut and hides the jump. This does not allow extra zooms: the count above
  still applies.
- **At least 4 s between any two zoom changes in the finished reel.** The server drops a change that comes
  too soon, and then the zoom sticks for the rest of the reel. The finished reel is shorter than the
  source (long pauses are shortened), so check every pair of neighbouring zoom changes with BOTH tests:
  1. **Words**: count the kept words from the first zoom word up to (not including) the next zoom word.
     At least **13**.
  2. **Time**: the `start_s` of the next zoom word minus the `start_s` of the first, minus every pause in
     between beyond 0.4 s, minus everything you cut in between. At least **5 s**.
  If either test fails, move the second change to a later sentence start that passes both, or punch in
  one clause earlier. A strong line is often a short sentence: then the zoom stays on through the next
  sentence or two before it goes back to 1.0. That is fine.
- Never two punch-ins in a row without going back to 1.0 in between. Every punch-in is followed by a
  1.0, unless it runs to the very end of the reel.
- `zoom` events are in kept order and every `at` is a kept word id. Never use `push_to`.

In the example (a reel of about 17 s): one punch-in on the key claim "The cheap one skips the flashing..."
at 30, and back to 1.0 at 53, the first word after the take cut, so the change also hides that cut.
Words: 30 to 44 are 15 kept words. Time: 22.40 - 12.60 = 9.8 s, minus the cut part from 17.80 to 22.40
(4.6 s) = 5.2 s. Both tests pass.

## Step 6: Caption corrections (only when needed)

Captions show the transcript words in capitals. Use `text` only for:

- **Clear mis-hearings**: a sound-alike that contradicts the meaning or the script ("flushing" where the
  speaker clearly says "flashing": `{"35": "FLASHING"}`).
- **Number formatting**: `{"40": "250,000"}`; for a number spread over several words, put it on the first
  word and hide the rest with `""` (`""` hides a word in the captions, its sound stays).
- A word the transcriber invented that is not spoken: hide it with `""`.

A garbled stretch inside a sentence you keep (for example a number the transcriber split into odd words,
"two X in your" for "to 2x your") is fixed here with `text`, never by cutting.
Never use `text` to change what was said. No emphasis list: the template has no highlight words.
Note every correction in `meta.notes`.

## Step 7: Dramatic pauses (optional, rare)

The server shortens every long pause. If the speaker leaves a deliberate pause for effect (the last words
said one at a time, a beat before the punchline), you may keep some of it:
`"pauses": {"hold_after": [ids of the words before the pause], "hold_max": 0.6}`. Do not set any other
`pauses` key.

## Self-check before start_render

1. `version` is 2 and `words_fingerprint` is copied exactly.
2. `keep`: ascending, no overlaps, every boundary sits at a pause of at least 0.25 s.
3. Read the kept text from start to end: every sentence of the script exactly once, complete, in order.
   No restart, no slip, no chatter before or after, no mumbled stretch.
4. Hook: 1 to 3 short lines, sentence case, only the clip's own words or what they clearly imply.
5. Zoom: punch-ins 1.12 to 1.18 on at most 1 to 3 lines per minute, each followed by 1.0 at a later
   sentence start, no rhythm, no `push_to`. Write down the word count and the time for every pair of
   neighbouring zoom changes: at least 13 words AND at least 5 s each, or move the change.
6. None of these keys anywhere: `whoosh`, `broll`, `music`, `sfx`, `captions`, `style`, `output`.
   No emojis.

## When the quality check fails (get_render qa.passed is false)

Fix the EDL for every line in `qa.issues`, then `start_render` again:

| qa.issues says | Fix |
|---|---|
| "re-transcript differs from the intended text ... a word may be clipped or lost" | A cut is too tight or a word got lost. Check the first and last word of every `keep` range: move the boundary to a bigger pause, or keep one more word on that side. Check you did not drop a single word inside a sentence. A word that lasts over 1.5 s is often a held sound: cut around it. |
| "... of the kept words are unclear (mumbled or off-script speech ...)" | You kept mumbled or off-script speech. Find the stretches of `unclear_word_ids` inside your `keep` ranges (chatter, a mumbled restart) and cut them. |
| "only X/Y cuts sit in silence" | Check every `keep` range start and end: move any that sits at a pause under 0.25 s to the biggest nearby pause and render again. If all of them already sit in pauses of 0.25 s or more, the unclean cut is one the server made inside a take while shortening a long pause: the EDL cannot move it. Do not change the takes and do not add `hold_after` for it; deliver the reel. |
| "captions cover the mouth in N frames" | Render again with `reel_style` `{"captions": {"position": "auto"}}`. |
| "loudness ... is off target" | Not an EDL problem. Render once more; if it stays, deliver and tell the user Reg's team will look at it. |

When `start_render` rejects the EDL, the error names the problem (for example a fingerprint that does not
match: copy it again from the latest `get_transcript`; a range that is reversed or overlaps; a zoom on a
word that is not kept). Fix exactly that and send it again.
