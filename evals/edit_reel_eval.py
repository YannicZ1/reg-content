#!/usr/bin/env python3
"""Eval for the edit-reel skill: does a Claude that follows the skill write EDLs that our renderer turns
into clean reels in Reg's template?

Per test clip:
  1. build the exact get_transcript result the client's Claude sees (the connector's own code),
  2. ask `claude -p` for the EDL, with SKILL.md + references/edl-guide.md (Claude subscription only:
     ANTHROPIC_API_KEY and friends are removed from the subprocess env, never API credits),
  3. check the EDL against the template rules (forbidden keys, zoom rules, hook from the clip's words),
  4. validate it with the renderer and render it with --verify (re-transcription, cut check, loudness),
  5. if the render's qa fails (the same gate as get_render in production), give Claude the qa result and let it
     fix the EDL like step 7 of the skill says (up to --fix-rounds), then check again,
  6. compare the kept text with the hand-written reference EDL.
A clip passes when its final EDL passes every check; "first pass" says whether it needed a fix round.

No clip data lives in this repo. It needs a local reel-engine checkout (REEL_ENGINE, default
~/Projects/reel-engine) with out/work/clip<N>.words.json (each names its source video in "source") and
renderer/examples/clip<N>.reg.edl.json (hand-written reference). Outputs go to --out (default: a temp dir).

usage: python3 evals/edit_reel_eval.py [--clips 1,2,3] [--out DIR] [--model opus] [--effort high]
                                       [--reuse] [--no-render] [--runs 1] [--fix-rounds 2]
exit 0 = every clip passes
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO / "plugins" / "content-system" / "skills" / "edit-reel"
ENGINE = Path(os.environ.get("REEL_ENGINE", "~/Projects/reel-engine")).expanduser()
PY = ENGINE / "renderer" / ".venv" / "bin" / "python"

# the delivery gate (same numbers as the connector's worker.qa_summary) + the template rules
MAX_WER = 0.03
LUFS = (-15.5, -12.5)
PUNCH = (1.12, 1.18)
MIN_GAP_S = 4.0
PER_MIN = 3
FORBIDDEN = {"whoosh", "broll", "music", "sfx", "push_to", "style", "output", "captions", "emphasis"}
SCRUB_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "CLAUDE_CODE_USE_BEDROCK",
             "CLAUDE_CODE_USE_VERTEX")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")

SYSTEM = ("You are Claude, an AI assistant made by Anthropic, chatting on claude.ai with a business owner "
          "who is one of Reg's clients. The plugin \"Reg's Content System\" is installed and the Reel Editor "
          "connector is on. Follow the plugin's skills exactly.")


# ------------------------------------------------------------------------------------------ inputs
def transcript_result(words_path: Path) -> dict:
    """What get_transcript returns when the upload is ready (built with the connector's own module)."""
    sys.path.insert(0, str(ENGINE / "connector"))
    from reel_connector import transcript as T  # noqa: E402

    words = T.load_words(words_path)
    dur = json.loads(words_path.read_text()).get("duration")
    return {"status": "ready", "upload_id": "up_eval", "duration_s": dur,
            "words_fingerprint": T.fingerprint(words_path), "text": T.plain_text(words),
            "word_format": ["id", "text", "start_s", "end_s"], "words": T.compact_words(words),
            "unclear_word_ids": [w["id"] for w in words if w.get("p", 1.0) < 0.6],
            "stats": T.summarize(words, dur)}


def build_prompt(tr: dict) -> str:
    skill = (SKILL_DIR / "SKILL.md").read_text()
    guide = (SKILL_DIR / "references" / "edl-guide.md").read_text()
    tr_json = json.dumps(tr, separators=(",", ":"), ensure_ascii=False)
    return f"""The user said: "edit my reel". They did not say which script it is.
You already called create_upload_link, the user uploaded the video, and get_transcript(upload_id) just returned
the result below. You are at step 5 of the edit-reel skill: write the EDL. Follow the skill and its reference
exactly, including the self-check.

<skill path="skills/edit-reel/SKILL.md">
{skill}
</skill>

<reference path="skills/edit-reel/references/edl-guide.md">
{guide}
</reference>

<tool_result name="get_transcript">
{tr_json}
</tool_result>

Reply with the EDL JSON object only, exactly as you would pass it as start_render's edl argument: no prose, no
code fence."""


def production_qa(rep: dict) -> dict:
    """get_render's `qa` for this render: same rules and issue texts as connector/reel_connector/worker.py
    qa_summary (keep the two in step)."""
    v = (rep.get("verify") or {}).get("summary") or {}
    issues = []
    wer = v.get("retranscript_wer")
    unclear = v.get("unclear_kept_share") or 0.0
    if wer is not None and wer > MAX_WER:
        if unclear >= 0.25:
            issues.append(f"{unclear:.0%} of the kept words are unclear (mumbled or off-script speech, low "
                          f"transcription confidence; re-transcript WER {wer:.2f}): consider cutting that part")
        else:
            issues.append(f"re-transcript differs from the intended text (WER {wer:.3f}): a word may be clipped or lost")
    cc = str(v.get("cuts_clean", ""))
    if "/" in cc:
        a, b = cc.split("/", 1)
        if a.strip() != b.strip():
            issues.append(f"only {cc} cuts sit in silence")
    if (v.get("mouth_overlap_frames") or 0) > 0:
        issues.append(f"captions cover the mouth in {v['mouth_overlap_frames']} frames")
    lufs = v.get("lufs")
    if lufs is not None and not LUFS[0] <= lufs <= LUFS[1]:
        issues.append(f"loudness {lufs} LUFS is off target (-14)")
    return {"passed": not issues, "issues": issues, "wer": wer, "unclear_kept_share": unclear, "cuts_clean": cc,
            "lufs": lufs, "mouth_overlap_frames": v.get("mouth_overlap_frames"), "music": None}


def build_fix_prompt(tr: dict, edl: dict, qa: dict, duration: float) -> str:
    """Step 7 of the skill: the render is done but get_render.qa.passed is false."""
    get_render = {"status": "done", "preview_url": "https://edit.example/p/job_eval", "download_url":
                  "https://edit.example/d/job_eval", "duration_s": round(duration, 2), "qa": qa,
                  "next": "Quality check found issues (see qa.issues). Fix the EDL (e.g. move the cut, keep the "
                          "clipped word) and re-render before giving this video to the user."}
    base = build_prompt(tr).rsplit("Reply with the EDL JSON object only", 1)[0]
    return base + f"""You wrote this EDL and called start_render with it:
<edl>
{json.dumps(edl, ensure_ascii=False)}
</edl>

get_render(job_id) just returned:
<tool_result name="get_render">
{json.dumps(get_render, ensure_ascii=False)}
</tool_result>

You are at step 7 of the edit-reel skill: qa.passed is false. Fix the EDL as the reference's table "When the quality
check fails" says, keeping every other rule. Reply with the fixed EDL JSON object only, exactly as you would pass it
to start_render: no prose, no code fence. If the reference says the EDL cannot fix this and you would deliver the
render as it is, reply with exactly {{"deliver": true}} instead."""


def ask_claude(prompt: str, model: str, effort: str, cwd: Path) -> tuple[dict | None, dict]:
    env = {k: v for k, v in os.environ.items() if k not in SCRUB_ENV}
    cmd = ["claude", "-p", "--model", model, "--effort", effort, "--tools", "", "--strict-mcp-config",
           "--setting-sources", "project", "--disable-slash-commands", "--no-session-persistence",
           "--output-format", "json", "--system-prompt", SYSTEM]
    t0 = time.time()
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, env=env, cwd=cwd, timeout=1800)
    info = {"seconds": round(time.time() - t0, 1), "returncode": r.returncode}
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        info["error"] = (r.stderr or r.stdout)[-2000:]
        return None, info
    info["models"] = list((out.get("modelUsage") or {}).keys())
    text = out.get("result") or ""
    info["raw"] = text
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        info["error"] = "no JSON object in the reply"
        return None, info
    try:
        return json.loads(m.group(0)), info
    except json.JSONDecodeError as e:
        info["error"] = f"reply is not valid JSON: {e}"
        return None, info


# ------------------------------------------------------------------------------------------ hook words
STOP = set("""a an the and or but so to of in on at for with by from as into about than then
is are was were be been being am do does did done have has had will would can could should shall may might must
i you your yours yourself we our us they them their he him his she her it its this that these those there here
my me mine what why how when where who which not no nor dont doesnt didnt wont cant isnt arent wasnt werent
just only very really more most all any every once until after before while because if since though
over through""".split())
# irregular forms count as the same word ("built" for "build")
IRREG = {"built": "build", "made": "make", "took": "take", "taken": "take", "lost": "lose", "said": "say",
         "went": "go", "gone": "go", "got": "get", "gave": "give", "given": "give", "thought": "think",
         "told": "tell", "bought": "buy", "sold": "sell", "taught": "teach", "kept": "keep", "left": "leave",
         "won": "win", "began": "begin", "begun": "begin", "ran": "run", "came": "come", "became": "become",
         "knew": "know", "known": "know", "saw": "see", "seen": "see", "found": "find", "felt": "feel",
         "paid": "pay", "spent": "spend", "grew": "grow", "grown": "grow", "brought": "bring", "meant": "mean",
         "chose": "choose", "chosen": "choose", "decided": "decide", "fell": "fall", "fallen": "fall"}
NUMS = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7",
        "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "twenty": "20"}


def toks(text: str) -> list[str]:
    out = []
    for raw in re.split(r"[\s/—–-]+", text.lower().replace("’", "'")):
        t = re.sub(r"^[^\w]+|[^\w']+$", "", raw)
        if not t:
            continue
        t = re.sub(r"n't$", "nt", t)
        t = re.sub(r"'(s|re|ve|ll|d|m)$", "", t).replace("'", "")
        if re.fullmatch(r"[\d,.]+k", t):
            t = str(int(float(t[:-1].replace(",", "")) * 1000))
        elif re.fullmatch(r"\d[\d,]*", t):
            t = t.replace(",", "")
        out.append(IRREG.get(NUMS.get(t, t), NUMS.get(t, t)))
    return out


def stem(t: str) -> str:
    for suf in ("ing", "ed", "es", "s", "ly"):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            return t[: -len(suf)]
    return t


def hook_unmatched(lines: list[str], kept_text: list[str]) -> list[str]:
    have = set(toks(" ".join(kept_text)))
    stems = {stem(t) for t in have}
    miss = []
    for t in toks(" ".join(lines)):
        if t in STOP or t in have or stem(t) in stems:
            continue
        if len(t) >= 5 and any(len(h) >= 5 and (h.startswith(t[:5]) and t.startswith(h[:5])) for h in have):
            continue
        miss.append(t)
    return miss


# ------------------------------------------------------------------------------------------ checks
def walk_keys(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, f"{path}.{k}" if path else k
            yield from walk_keys(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_keys(v, f"{path}[{i}]")


def kept_ids(edl: dict, words: dict) -> list[int]:
    ids = []
    for a, b in edl.get("keep") or []:
        ids += [i for i in range(a, b + 1) if i in words]
    return ids


def static_checks(edl: dict, words: dict, fp: str) -> tuple[list[str], list[str], list[str]]:
    F, W = [], []
    if edl.get("version") != 2:
        F.append("version is not 2")
    if edl.get("words_fingerprint") != fp:
        F.append(f"words_fingerprint {edl.get('words_fingerprint')!r} != {fp}")
    allowed_top = {"version", "words_fingerprint", "keep", "hook", "zoom", "text", "pauses", "meta"}
    for k in edl:
        if k not in allowed_top and k not in FORBIDDEN:  # the renderer ignores unknown keys
            W.append(f"unknown key (ignored by the renderer): {k!r}")
    for k, p in walk_keys({k: v for k, v in edl.items() if k != "meta"}):
        if k in FORBIDDEN:
            F.append(f"forbidden key: {p}")
    if set((edl.get("pauses") or {})) - {"hold_after", "hold_max"}:
        F.append(f"pauses sets more than hold_after/hold_max: {sorted(edl['pauses'])}")
    kept = kept_ids(edl, words)
    kset = set(kept)
    # cuts in pauses (source gaps on the cut side of every boundary)
    for a, b in edl.get("keep") or []:
        if a - 1 in words and words[a]["start"] - words[a - 1]["end"] < 0.25:
            W.append(f"range start {a} ({words[a]['text']!r}) has only "
                     f"{words[a]['start'] - words[a - 1]['end']:.2f} s before it")
        if b + 1 in words and words[b + 1]["start"] - words[b]["end"] < 0.25:
            W.append(f"range end {b} ({words[b]['text']!r}) has only "
                     f"{words[b + 1]['start'] - words[b]['end']:.2f} s after it")
    # hook
    hk = edl.get("hook")
    hook_miss = []
    if hk:
        lines = hk.get("lines") or []
        if not 1 <= len(lines) <= 3:
            F.append(f"hook has {len(lines)} lines (1-3)")
        for l in lines:
            if len(l) > 28:
                F.append(f"hook line too long ({len(l)} chars): {l!r}")
            elif len(l) > 24:
                W.append(f"hook line over 24 chars: {l!r}")
            letters = [c for c in l if c.isalpha()]
            if len(letters) > 3 and all(c.isupper() for c in letters):
                F.append(f"hook line in ALL CAPS, not sentence case: {l!r}")
            if EMOJI.search(l) or "#" in l:
                F.append(f"emoji/hashtag in hook: {l!r}")
        if lines and not lines[0][:1].isupper() and not lines[0][:1].isdigit():
            F.append(f"hook does not start with a capital: {lines[0]!r}")
        if sum(len(l.split()) for l in lines) > 12:
            W.append("hook over ~10 words")
        hook_miss = hook_unmatched(lines, [words[i]["text"] for i in kept])
        if len(hook_miss) > 1:
            F.append(f"hook words not in the kept clip: {hook_miss}")
        elif hook_miss:
            W.append(f"hook word not in the kept clip (check it is clearly implied): {hook_miss}")
        if set(hk) - {"lines"}:
            W.append(f"hook has extra keys {sorted(set(hk) - {'lines'})} (the look sets them)")
    else:
        W.append("no hook")
    for k, v in (edl.get("text") or {}).items():
        if EMOJI.search(str(v)):
            F.append(f"emoji in caption override {k}")
    # zoom
    zl = edl.get("zoom") or []
    prev_scale, prev_was_punch = 1.0, False
    starts = {a for a, _ in edl.get("keep") or []}
    for z in zl:
        s = float(z.get("scale", 1.0))
        if z.get("at") not in kset:
            F.append(f"zoom at {z.get('at')} is not a kept word")
            continue
        if s != 1.0 and not PUNCH[0] <= s <= PUNCH[1]:
            F.append(f"zoom scale {s} at {z['at']} outside 1.0 / {PUNCH[0]}-{PUNCH[1]}")
        if s > 1.0 and prev_was_punch:
            F.append(f"two punch-ins in a row (no 1.0 between) at {z['at']}")
        if s == 1.0 and prev_scale == 1.0 and z is not zl[0]:
            W.append(f"zoom back to 1.0 at {z['at']} while already at 1.0")
        if s == 1.0 and prev_was_punch:
            i = kept.index(z["at"])
            prev_txt = words[kept[i - 1]]["text"] if i else ""
            if z["at"] not in starts and not re.search(r"[.?!][\"')\]]*$", prev_txt):
                W.append(f"zoom out at {z['at']} ({words[z['at']]['text']!r}) is not at a sentence start "
                         f"(previous word {prev_txt!r})")
        prev_was_punch = s > 1.0
        prev_scale = s
    return F, W, hook_miss


def run_validate(edl_path: Path, words_path: Path) -> tuple[list[str], list[str]]:
    r = subprocess.run([str(PY), "-m", "renderer.edl", "--edl", str(edl_path), "--words", str(words_path)],
                       cwd=ENGINE, capture_output=True, text=True)
    errs = [l[6:] for l in r.stdout.splitlines() if l.startswith("ERROR")]
    warns = [l[6:] for l in r.stdout.splitlines() if l.startswith("WARN")]
    if r.returncode and not errs:
        errs.append((r.stderr or r.stdout)[-500:])
    return errs, warns


def run_render(src: str, words_path: Path, edl_path: Path, out_mp4: Path, qa_dir: Path) -> dict:
    empty = out_mp4.parent / "empty.profile.json"
    empty.write_text("{}")
    log = out_mp4.with_suffix(".render.log")
    with open(log, "w") as fh:
        r = subprocess.run([str(PY), "-m", "renderer.render", "--src", src, "--words", str(words_path),
                            "--edl", str(edl_path), "--profile", str(empty), "--out", str(out_mp4),
                            "--qa-dir", str(qa_dir), "--verify"], cwd=ENGINE, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(f"render failed, see {log}")
    return json.loads(Path(str(out_mp4) + ".report.json").read_text())


def render_checks(rep: dict, edl: dict) -> tuple[list[str], list[str], dict]:
    F, W = [], []
    v = (rep.get("verify") or {}).get("summary") or {}
    wer = v.get("retranscript_wer")
    if wer is None or wer > MAX_WER:
        F.append(f"verify WER {wer} > {MAX_WER}")
    cc = str(v.get("cuts_clean", ""))
    a, _, b = cc.partition("/")
    bad_cuts = [f"{c['kind']} cut {c['left_word']}->{c['right_word']} ({vc['level_before_db']}/{vc['level_after_db']} dB, "
                f"limit {vc['limit_db']})" for c, vc in zip(rep.get("cuts") or [], (rep.get("verify") or {}).get("cuts") or [])
                if not vc["ok"]]
    if not b or a.strip() != b.strip():
        who = ("a 'take' cut is a keep boundary (the EDL's job); a 'pause' cut is the server shortening a pause "
               "inside a take (renderer)")
        F.append(f"cuts clean {cc}: {'; '.join(bad_cuts)} [{who}]")
    if (v.get("mouth_overlap_frames") or 0) > 0:
        F.append(f"captions over the mouth in {v['mouth_overlap_frames']} frames")
    lufs = v.get("lufs")
    if lufs is None or not LUFS[0] <= lufs <= LUFS[1]:
        F.append(f"loudness {lufs} LUFS off target")
    dur = rep["duration_out_s"]
    fps = rep["frames"] / dur if dur else 30
    # zoom as rendered (after the renderer's 4 s guard): change times and punch-ins
    changes, prev = [], 1.0
    for iv in rep.get("zoom") or []:
        if iv["scale"] != prev:
            changes.append((iv["f0"] / fps, iv["scale"]))
            prev = iv["scale"]
    edl_changes, prev = 0, 1.0
    for z in edl.get("zoom") or []:
        if float(z.get("scale", 1.0)) != prev:
            edl_changes += 1
            prev = float(z.get("scale", 1.0))
    if len(changes) != edl_changes:
        F.append(f"renderer dropped zoom changes ({edl_changes} in the EDL, {len(changes)} rendered): "
                 "a change came < 4 s after the previous one")
    gaps = [round(t2 - t1, 2) for (t1, _), (t2, _) in zip(changes, changes[1:])]
    if gaps and min(gaps) < MIN_GAP_S:
        F.append(f"zoom changes {min(gaps)} s apart (< {MIN_GAP_S})")
    punches = sum(1 for _, s in changes if s > 1.0)
    allowed = max(1, math.floor(PER_MIN * dur / 60 + 0.5))
    if punches > allowed:
        F.append(f"{punches} punch-ins in {dur:.1f} s (max {allowed} = {PER_MIN}/min)")
    if rep.get("sfx_whooshes"):
        F.append(f"{rep['sfx_whooshes']} sound effects rendered")
    if rep.get("broll"):
        F.append("b-roll rendered")
    for w in rep.get("warnings") or []:
        W.append(f"renderer: {w}")
    m = {"duration_out_s": round(dur, 1), "wer": wer, "cuts_clean": cc, "lufs": lufs,
         "mouth_overlap_frames": v.get("mouth_overlap_frames"), "punch_ins": punches, "punch_ins_allowed": allowed,
         "zoom_changes_s": [round(t, 1) for t, _ in changes], "zoom_gaps_s": gaps,
         "retranscript_diffs": v.get("retranscript_diffs"), "unclear_kept_share": v.get("unclear_kept_share"),
         "qa_frames": rep.get("qa_frames")}
    return F, W, m


def compare_reference(edl: dict, ref: dict, words: dict) -> dict:
    a, b = set(kept_ids(edl, words)), set(kept_ids(ref, words))

    def spans(ids):
        out, run = [], []
        for i in sorted(ids):
            if run and i != run[-1] + 1:
                out.append(run)
                run = []
            run.append(i)
        if run:
            out.append(run)
        return [f"[{r[0]}-{r[-1]}] " + " ".join(words[i]["text"] for i in r) for r in out]

    return {"skill_keep": edl.get("keep"), "reference_keep": ref.get("keep"),
            "only_in_skill": spans(a - b), "only_in_reference": spans(b - a),
            "overlap": round(len(a & b) / max(1, len(a | b)), 3)}


# ------------------------------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clips", default="1,2,3")
    ap.add_argument("--out", help="output dir (default: a new temp dir)")
    ap.add_argument("--model", default="opus")
    ap.add_argument("--effort", default="high", help="the setup guide tells clients to use High")
    ap.add_argument("--runs", type=int, default=1, help="EDLs to ask for per clip (each is checked)")
    ap.add_argument("--reuse", action="store_true", help="reuse EDLs already in --out instead of asking Claude")
    ap.add_argument("--no-render", action="store_true", help="static checks + validation only")
    ap.add_argument("--fix-rounds", type=int, default=2,
                    help="like step 7 of the skill: when the render's qa fails, Claude fixes the EDL (0 = off)")
    a = ap.parse_args()
    out = Path(a.out or tempfile.mkdtemp(prefix="edit-reel-eval-")).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "qa").mkdir(exist_ok=True)
    clips = [int(c) for c in a.clips.split(",") if c.strip()]
    jobs = [(c, r) for c in clips for r in range(1, a.runs + 1)]

    def name(c, r):
        return f"clip{c}-skill" + (f"-r{r}" if a.runs > 1 else "")

    def get_edl(job):
        c, r = job
        words_path = ENGINE / "out" / "work" / f"clip{c}.words.json"
        edl_path = out / f"{name(c, r)}.edl.json"
        if a.reuse and edl_path.exists():
            return job, json.loads(edl_path.read_text()), {"reused": True}
        tr = transcript_result(words_path)
        prompt = build_prompt(tr)
        (out / f"clip{c}.prompt.txt").write_text(prompt)
        edl, info = ask_claude(prompt, a.model, a.effort, out)
        (out / f"{name(c, r)}.claude.json").write_text(json.dumps(info, indent=1))
        if edl is not None:
            edl_path.write_text(json.dumps(edl, indent=1))
        return job, edl, info

    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        got = list(ex.map(get_edl, jobs))

    def evaluate(c, label, edl, words_path, wj, words):
        """All checks for one EDL. -> (result dict, production qa or None)"""
        edl_path = out / f"{label}.edl.json"
        edl_path.write_text(json.dumps(edl, indent=1))
        fp = transcript_result(words_path)["words_fingerprint"]
        F, W, hook_miss = static_checks(edl, words, fp)
        verr, vwarn = run_validate(edl_path, words_path)
        F += [f"validator: {e}" for e in verr]
        for w in vwarn:
            (F if "cannot sit in silence" in w else W).append(f"validator: {w}")
        res = {"hook": (edl.get("hook") or {}).get("lines"), "hook_unmatched_words": hook_miss,
               "keep": edl.get("keep"), "zoom": edl.get("zoom"), "text_overrides": edl.get("text"),
               "pauses": edl.get("pauses"), "notes": (edl.get("meta") or {}).get("notes")}
        ref_path = ENGINE / "renderer" / "examples" / f"clip{c}.reg.edl.json"
        if ref_path.exists():
            res["vs_reference"] = compare_reference(edl, json.loads(ref_path.read_text()), words)
        qa = None
        if not a.no_render and not verr:
            try:
                rep = run_render(wj["source"], words_path, edl_path, out / f"{label}.mp4", out / "qa")
                rf, rw, m = render_checks(rep, edl)
                F += rf
                W += rw
                res["render"] = m
                qa = production_qa(rep)
                res["production_qa"] = qa
            except Exception as e:  # noqa: BLE001
                F.append(str(e))
        res.update(passed=not F, fails=F, warns=W)
        return res, qa

    results, all_ok = [], True
    for (c, r), edl, info in got:
        words_path = ENGINE / "out" / "work" / f"clip{c}.words.json"
        wj = json.loads(words_path.read_text())
        words = {w["id"]: w for w in wj["words"]}
        res = {"clip": c, "run": r, "name": name(c, r), "claude": {k: v for k, v in info.items() if k != "raw"}}
        if edl is None:
            res.update(passed=False, fails=[f"no EDL: {info.get('error')}"], warns=[], rounds=[])
            results.append(res)
            all_ok = False
            continue
        rounds = []
        label = name(c, r)
        cur, qa = evaluate(c, label, edl, words_path, wj, words)
        rounds.append(cur)
        # step 7 of the skill: qa.passed false -> the client's Claude fixes the EDL and renders again (max 2 rounds)
        while qa is not None and not qa["passed"] and len(rounds) <= a.fix_rounds:
            tr = transcript_result(words_path)
            prompt = build_fix_prompt(tr, edl, qa, cur["render"]["duration_out_s"])
            fixed, finfo = ask_claude(prompt, a.model, a.effort, out)
            flabel = f"{label}-fix{len(rounds)}"
            (out / f"{flabel}.claude.json").write_text(json.dumps(finfo, indent=1))
            if fixed is None:
                cur = {"passed": False, "fails": [f"no fixed EDL: {finfo.get('error')}"], "warns": []}
                rounds.append(cur)
                break
            if fixed.get("deliver") is True or {k: v for k, v in fixed.items() if k != "meta"} == \
                    {k: v for k, v in edl.items() if k != "meta"}:
                # the skill decided the EDL cannot fix it and delivers this render (no second render)
                cur = {**cur, "delivered_without_fix": qa["issues"]}
                break
            edl = fixed
            cur, qa = evaluate(c, flabel, edl, words_path, wj, words)
            rounds.append(cur)
        res.update(cur)
        res["first_pass"] = rounds[0]["passed"]
        if cur.get("delivered_without_fix"):
            res["warns"] = res["warns"] + [f"skill judged these qa issues not fixable in the EDL and delivered: "
                                           f"{cur['delivered_without_fix']}"]
        res["rounds"] = [{"passed": x["passed"], "fails": x["fails"], "keep": x.get("keep"), "pauses": x.get("pauses"),
                          "qa_issues": (x.get("production_qa") or {}).get("issues")} for x in rounds]
        all_ok &= res["passed"]
        results.append(res)

    (out / "summary.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
    for res in results:
        m = res.get("render") or {}
        rounds = res.get("rounds") or []
        if len(rounds) > 1:
            for i, x in enumerate(rounds[:-1]):
                print(f"\n-- {res['name']} round {i + 1}: {'PASS' if x['passed'] else 'FAIL'} qa {x['qa_issues']} "
                      f"fails {x['fails']}")
        print(f"\n== {res['name']}: {'PASS' if res['passed'] else 'FAIL'}"
              f"{' (after %d fix round%s)' % (len(rounds) - 1, 's' if len(rounds) > 2 else '') if len(rounds) > 1 else ''}  "
              f"WER {m.get('wer')}  cuts {m.get('cuts_clean')}  punch-ins {m.get('punch_ins')}/"
              f"{m.get('punch_ins_allowed')}  zoom at {m.get('zoom_changes_s')} gaps {m.get('zoom_gaps_s')}  "
              f"duration {m.get('duration_out_s')} s  LUFS {m.get('lufs')}")
        print(f"   first pass: {'PASS' if res.get('first_pass') else 'FAIL'}  hook: {res.get('hook')}  "
              f"unmatched: {res.get('hook_unmatched_words')}  pauses: {res.get('pauses')}")
        vr = res.get("vs_reference") or {}
        if vr:
            print(f"   keep {vr['skill_keep']} vs reference {vr['reference_keep']} (overlap {vr['overlap']})")
            for s in vr["only_in_skill"]:
                print(f"     + {s}")
            for s in vr["only_in_reference"]:
                print(f"     - {s}")
        for f in res["fails"]:
            print(f"   FAIL {f}")
        for w in res["warns"]:
            print(f"   warn {w}")
    print(f"\n{sum(r['passed'] for r in results)}/{len(results)} passed. Outputs: {out}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
