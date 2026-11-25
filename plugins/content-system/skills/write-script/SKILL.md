---
name: write-script
description: Write one short-form video script (Instagram Reel, talking to camera) in Reg's format, using only the facts in the user's Content Brain and what they say in the chat. Use whenever the user asks for a script, a reel, a video, "write idea 3", "turn this into a video", "script for this week", or picks an idea from a list of content ideas.
---

**Step 0, always first: get the current version of this skill.** This file is version 2.1.0 of the skill.
Reg's team keeps the newest version on the Reel Editor server. Call the Reel Editor connector's `get_playbook`
tool with name "write-script". If it returns a text whose `version` is 2.1.0 or newer, follow that text
instead of this file, and get any reference file it names with `get_playbook` (name "write-script", reference
= the file's path, e.g. "references/..."). Skip this step if you are already reading the text from
`get_playbook`. If the tool is not available or the call fails, go on with this file and do not mention it.

# Write a script in Reg's format

You write scripts for a business owner who films them on their phone. Every script must sound like them, be
true, and be in Reg's exact format. Your output is judged against the ten scripts Reg's team wrote for them.

## 1. Load what you know (every time)

- Read the Project file **content-brain.md**: the owner's own answers from the Script Creation Form. It is
  the ONLY source of facts about them besides what they tell you in this chat.
- Read the Project file **my-first-10-scripts.md**: the voice, length and format to match. Scripts 1-4 reach
  new people, 5-8 build trust with buyers, 9-10 sell with a comment keyword.
- If either file is missing, say so in one line and ask the user to add it to the Project (their setup guide
  shows how). If they want to go on anyway, use what they paste into the chat.
- Never repeat an idea or a hook move that is already in my-first-10-scripts.md or earlier in this chat.

## 2. Pick the lane

| Lane | Job | The business shows up as |
|---|---|---|
| Reach (TOFU) | stop strangers who never heard of them, no offer | lived experience only ("someone who has worked the sites") |
| Trust (MOFU) | show buyers how to think about the problem | at most one first-person line, never a credential plug |
| Sell (BOFU) | one real customer or the real math, then the keyword | the offer, plus "comment WORD below" |

If the user did not say, pick the lane the idea fits and name it in your last line.
The viewer's problem is the topic. Test: delete every mention of the business. If the script still moves
the viewer, it is right.

## 3. Facts: only what is true

- Use only facts, stories, numbers, prices, customers and quotes from content-brain.md or this chat.
- If the script needs a detail you do not have (a real job, a price, a customer, a number), ask ONE short
  question before writing, for example: "Which real job from the last month should this be about?"
- Never invent a customer, a number, a quote, a credential, an award or a result. Never name a competitor or a
  real person. Anything the brain marks off limits is never used. Stories marked anonymous stay anonymous.
- Customer quotes become reported speech ("a customer told me my crew left the place cleaner than they found it").
- Sensitive moments are implied, never spelled out. Soften facts to what is safe to say in public.

## 4. The format (exactly this, nothing else)

```
[3-SECOND HOOK / TITLE]
THE HOOK IN CAPITALS. A PARADOX OR A TWO-BEAT TURN. 9 TO 20 WORDS.
[BODY]
One sentence per line.

A blank line between sentences.
[CLIMAX]
...
[CLIMACTIC ENDING]
...
```

- 200 to 375 spoken words, aim for about 250.
- No stage directions, no "on screen" notes, no "Format:" or "Film it:" lines, no lists or bullet points,
  no emoji, no hashtags, no em or en dashes.

## 5. The register (Reg's moves)

1. **Hook = the title, in capitals.** A paradox, an antithesis, or a dramatic two-beat statement about the
   viewer's problem.
2. **The body pulls the viewer in at once:** a question to them ("Have you ever..."), an invitation ("If you
   own a home, let me tell you what..."), or a scene they can see.
3. **Formal, deliberate cadence.** Write verbs out: do not, is not, cannot, I have. At most one contraction.
   Short declaratives. Fragments for rhythm. Triads.
4. **An image on almost every beat, always about the concrete thing:** give objects a will ("water does not
   attack the middle of a roof, it waits at the edges"), compress an idea into a picture ("a bill that has not
   arrived yet").
5. **Antithesis is the engine.** "The report is not protection. The follow-up is protection."
6. **Climax = a stack or a split.** Three lines of "X is not Y", or "there are two kinds of...". Use the
   ellipsis character (…) to hold the beat before the turn.
7. **Ending = the viewer looks at their own situation, then one line that lingers.** Story scripts end by
   speaking to a group ("To every owner who...") with short commands.
8. **Sell (BOFU) ending:** "If you [situation], comment WORD below." then "I will send you [the real thing] myself."
   then either one closing value line or nothing. WORD is one short word in capitals that fits the offer.
   The thing you promise to send must be something the brain says they offer (a price list, class dates, a
   quote, photos). If the brain does not say, ask "What do you send people who comment?" before writing.
9. **Even less business than feels natural.** No credentials, no "we are the best", no company pitch.
10. **No lists.** Turn a list into prose commands ("Stop treating it like paperwork. Do not wait for...").
11. **Widen the audience inside a line** when it fits ("Somebody's father. Somebody's daughter.").

Never use these: journey, game-changer, let's dive in, here's the thing, in today's world, unlock, elevate
your, buckle up, at the end of the day, secret, hack. No hype, no slang the owner would not use (check
"How do you actually talk?" in the brain).

If my-first-10-scripts.md is missing, the example in `references/example-script.md` shows the shape. Use it
for structure only, never its sentences or topic.

## 6. Check before you show it

If you can run code, save the script to a file and run:

`python3 scripts/check_script.py script.txt --lane tofu|mofu|bofu`

Fix every ERROR and run it again until it prints 0 errors. If you cannot run code, check the same points by
hand: capitals hook of 9 to 20 words, the four labels in order, 200 to 375 words, one sentence per line, at
most one contraction, no banned words, no dashes, keyword only in a Sell script and always in one.

Then read it once as the owner, out loud in your head. Cut any line they would not say. Cut any fact you
cannot point to in the brain or the chat.

## 7. Deliver

- No introduction, no report about the checker. Start with the script itself, as plain text (not in a code
  block), so they can paste it into a teleprompter app.
- Under it, one short line: the lane and what it is built from, for example
  "Trust lane, built from: What do customers always get wrong."
- Only if something must be checked before posting (a price or date that may be old, a promise the brain does
  not back up, a place name that could identify someone), add ONE line: "Check before you post: ..."
- Then one offer, nothing more: "Want changes? Tell me what to make shorter, harder or warmer."
