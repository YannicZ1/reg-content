#!/usr/bin/env python3
"""Check one script against Reg's format. Exit 0 = clean (warnings allowed), 1 = fix the errors.

Usage: python3 check_script.py script.txt --lane tofu|mofu|bofu
The file holds one script: optional "SCRIPT n" line, then the four labels on their own lines:
  [3-SECOND HOOK / TITLE]  [BODY]  [CLIMAX]  [CLIMACTIC ENDING]
Thresholds come from Reg's own rewrites (avg 256 words, range 199-374, about one sentence per line,
0-1 verb contractions). Truth and voice are checked by reading, not here. Standard library only.
"""
import argparse
import re
import sys

LABELS = ["3-SECOND HOOK / TITLE", "BODY", "CLIMAX", "CLIMACTIC ENDING"]
LABEL_LINE = re.compile(r"^\[([A-Z0-9 /-]+)\]\s*$", re.M)
WORD = re.compile(r"[A-Za-z0-9$%’']+")
CONTRACTION = re.compile(r"\b\w+(?:n[’']t|[’'](?:re|ve|ll|m|d))\b", re.I)
SENT_END = re.compile(r"[.?!…](?=\s|$|[”\"'])")
KEYWORD_CTA = re.compile(r"\b(?i:comment) ([A-Z]{3,})\b")
BANNED = ["journey", "game-changer", "game changer", "let's dive", "dive into", "here's the thing",
          "in today's world", "unlock", "elevate your", "buckle up", "at the end of the day", "hack",
          "secret sauce", "manychat"]
STAGE = ["[on screen", "on screen:", "format:", "film it", "[write ", "[circle", "b-roll", "(pause", "[pause"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def check(text, lane):
    errors, warns = [], []
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"^\s*SCRIPT \d+\s*$", "", text, flags=re.M)
    for ch, name in (("—", "em dash"), ("–", "en dash")):
        if ch in text:
            errors.append(f"contains an {name}: use a full stop, a comma or a new line")
    found = [m.group(1) for m in LABEL_LINE.finditer(text)]
    if found != LABELS:
        errors.append(f"labels must be exactly {LABELS} in this order, found {found}")
    marks = list(LABEL_LINE.finditer(text))
    parts = {}
    for i, m in enumerate(marks):
        stop = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        parts[m.group(1)] = text[m.end():stop].strip()
    hook = parts.get(LABELS[0], "")
    letters = re.sub(r"[^A-Za-z]", "", hook)
    if not letters or letters != letters.upper():
        errors.append("the hook/title must be in CAPITALS")
    hw = len(WORD.findall(hook))
    if not 6 <= hw <= 24:
        errors.append(f"the hook has {hw} words (aim for 9 to 20)")
    elif not 9 <= hw <= 20:
        warns.append(f"the hook has {hw} words (aim for 9 to 20)")
    spoken = "\n".join(parts.values())
    words = len(WORD.findall(spoken))
    if not 180 <= words <= 400:
        errors.append(f"{words} words (allowed 180 to 400, aim for about 250)")
    elif not 195 <= words <= 380:
        warns.append(f"{words} words (aim for 200 to 375)")
    lines = [l for l in spoken.split("\n") if l.strip()]
    multi = [l for l in lines if len(SENT_END.findall(l)) > 2]
    ratio = sum(max(1, len(SENT_END.findall(l))) for l in lines) / max(1, len(lines))
    if ratio > 1.4 or multi:
        errors.append(f"one sentence per line, please ({len(multi)} lines hold 3 or more sentences)")
    c = CONTRACTION.findall(spoken)
    if len(c) > 3:
        errors.append(f"{len(c)} contractions {c}: write them out (do not, is not, cannot)")
    elif len(c) > 1:
        warns.append(f"{len(c)} contractions {c}: Reg uses at most one")
    low = text.lower()
    for b in BANNED:
        if re.search(r"\b" + re.escape(b) + r"\b", low):
            errors.append(f"banned phrase '{b}'")
    for s in STAGE:
        if s in low:
            errors.append(f"stage or format note '{s}' does not belong in the script")
    if EMOJI.search(text):
        errors.append("emoji")
    if re.search(r"(?<![\w/&])#[A-Za-z]\w+", text):
        errors.append("hashtag")
    if re.search(r"^\s*([-*•]|\d+[.)])\s", spoken, re.M):
        errors.append("list or bullet points: turn them into sentences")
    cta = KEYWORD_CTA.search(parts.get("CLIMACTIC ENDING", ""))
    if lane == "bofu" and not cta:
        errors.append("a Sell (BOFU) script ends with 'comment WORD below' (WORD in capitals)")
    if lane != "bofu" and KEYWORD_CTA.search(spoken):
        errors.append("only a Sell (BOFU) script gets a 'comment WORD' line")
    return errors, warns, words, ratio, len(c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--lane", choices=["tofu", "mofu", "bofu"], required=True)
    a = ap.parse_args()
    errors, warns, words, ratio, contr = check(open(a.file, encoding="utf-8").read(), a.lane)
    print(f"{a.lane.upper()}  {words} words  {ratio:.2f} sentences/line  {contr} contractions")
    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"{len(errors)} errors, {len(warns)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
