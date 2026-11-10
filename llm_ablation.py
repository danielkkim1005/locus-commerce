"""Run a model against the frozen codebook and measure what the codebook's parts
are each worth.

    python llm_ablation.py --backend stub                  # no API key, end to end
    python llm_ablation.py --backend openai --model gpt-5.4-nano --repeats 5
    python llm_ablation.py --dry-run --variant E           # print a prompt, call nothing

The question this answers is not "can a model label commerce". It is whether a
specification written for humans is the right specification for a model. Round 1
ran under a one-paragraph definition and gave Fleiss' kappa 0.232; round 2 ran
under a procedural codebook and gave 0.549, 0.724 on legible rows. That is
evidence proceduralizing helped the humans. The hypothesis here is that the model
is the mirror image - that a procedure is control flow, and a forward pass has no
control flow, so sequential steps buy a model less than worked examples do,
because retrieval over exemplars is what attention does natively.

Five prompt variants, composed from the fragments in prompts/:

    A  core test only                      baseline
    B  A + the four-step procedure         isolates the procedure
    C  B + reason codes with carve-outs    isolates the carve-out prose
    D  core test + examples, NO procedure  isolates the edge-case log
    E  everything                          the shipped codebook

B minus A is what the procedure is worth. D minus C is the edge-case log against
the carve-out prose. E minus C is what examples add on top of a full procedural
rendering. If D beats B while the human record runs the other way, the
instruction format is audience-dependent and that is the finding.

Length is a confound and is not controlled: --dry-run reports roughly 1.0k, 1.5k,
2.5k, 3.2k and 4.5k tokens for A through E, so D is about a quarter longer than C.
If D wins, check it is not winning on length alone by trimming the example set
and rerunning; if three examples do what eleven do, length was not the mechanism.

Four design decisions that keep the answer honest:

Held-out evaluation. The 75 round-2 rows are the gold set, so selecting a prompt
on them overfits and the reported number means nothing. Develop on round 1
(--eval round1, a binary core-vs-rest proxy, since round 1 asked yes/no), then
evaluate on round 2 ONCE. --split holds out a fraction of round 2 instead if the
round-1 sheets are not to hand.

Reasoning before the label. The output contract puts "reasoning" first. Asked for
a bare tier, a model computes the label in one pass and then confabulates a step
number to match, which would make the procedure arms look weak for the wrong
reason. Writing the steps out puts the computation somewhere later positions can
attend to.

Forced abstention. "no-context" is in the label space with worked examples, and
the procedure asks what party and what activity the text names before offering a
tier. Models answer anyway by default; abstention has to fall out of a failed
extraction rather than be requested politely.

Permuted orderings. Reason codes and examples are shuffled per repeat with a
seeded RNG. Position effects on an eight-item list are real, and the spread
across permutations is itself a measurement.

Outputs, in labels/:

    llm_runs.csv        one line per call: variant, row, repeat, parsed fields
    llm_rowstats.csv    per row: model self-agreement, human disagreement
    llm_ablation.txt    the printed report

Responses are cached under out/llm_cache/ keyed by the exact prompt, so a rerun
costs nothing and an interrupted run resumes.
"""

import argparse
import collections
import csv
import hashlib
import json
import os
import pathlib
import random
import re
import statistics
import sys
import time
import urllib.error
import urllib.request

from merge_labels import fleiss_kappa, majority
from merge_round2 import gwet_ac1

TIERS = ["core", "adjacent", "not"]
OUTCOMES = TIERS + ["unresolvable"]
REASONS = ["gov-market", "revenue", "land-use", "general-law",
           "counterparty", "procedure", "definition", "sometimes-business"]
CATEGORIES = ["entry", "operation", "exit", "other"]

# fragment stack per variant; "reasons" and "examples" are rendered, not read raw
VARIANTS = {
    "A": ["task", "core_test", "label_space", "output_contract"],
    "B": ["task", "core_test", "procedure", "label_space", "output_contract"],
    "C": ["task", "core_test", "procedure", "label_space", "reasons",
          "categories", "output_contract"],
    "D": ["task", "core_test", "label_space", "categories", "examples",
          "output_contract"],
    "E": ["task", "core_test", "procedure", "label_space", "reasons",
          "categories", "examples", "output_contract"],
}


# ---------------------------------------------------------------- prompt build

def load_fragments(pdir: pathlib.Path) -> dict:
    frags = {}
    for name in ("task", "core_test", "procedure", "label_space", "categories",
                 "output_contract"):
        frags[name] = (pdir / f"{name}.md").read_text(encoding="utf-8").strip()
    frags["_reasons"] = json.loads((pdir / "reason_codes.json").read_text(encoding="utf-8"))
    frags["_examples"] = json.loads((pdir / "examples.json").read_text(encoding="utf-8"))
    return frags


def render_reasons(reasons: list, rng: random.Random) -> str:
    order = reasons[:]
    rng.shuffle(order)
    out = ["# Adjacent reason codes",
           "",
           "Each carries a carve-out. The carve-outs are rulings, not suggestions."]
    for r in order:
        out += ["", f"## {r['code']}", r["body"]]
    return "\n".join(out)


def render_examples(examples: list, rng: random.Random) -> str:
    order = examples[:]
    rng.shuffle(order)
    out = ["# Worked examples",
           "",
           "References, not templates. Classify each new excerpt on its own terms."]
    for e in order:
        f = e["fields"]
        out += ["",
                f"## Example: {e['id']}",
                "Text:",
                e["text"],
                "",
                f"Why: {e['why']}",
                "",
                "Answer: " + json.dumps(f, separators=(", ", ": "))]
    return "\n".join(out)


def build_prompt(variant: str, frags: dict, excerpt: str, header: str,
                 rng: random.Random) -> str:
    parts = []
    for name in VARIANTS[variant]:
        if name == "reasons":
            parts.append(render_reasons(frags["_reasons"], rng))
        elif name == "examples":
            parts.append(render_examples(frags["_examples"], rng))
        else:
            parts.append(frags[name])
    # The excerpt goes last, closest to generation.
    parts.append("# Excerpt to classify\n\n"
                 f"Section header: {header}\n\nText:\n{excerpt}")
    return "\n\n---\n\n".join(parts)


# ------------------------------------------------------------------- backends

def call_stub(prompt: str, model: str, temperature: float) -> str:
    """Deterministic pseudo-labels so the whole pipeline runs with no API key.

    Keyed off the excerpt, with a little prompt-dependent jitter so variants and
    repeats are not identical. Exercises the parser, the metrics and the report;
    the numbers it produces mean nothing.
    """
    excerpt = prompt.rsplit("Text:\n", 1)[-1].lower()
    h = int(hashlib.sha1(prompt.encode()).hexdigest(), 16)
    if len(excerpt) < 240 and ("this article" in excerpt or "this subtitle" in excerpt):
        obj = {"tier": "", "unresolvable": "no-context", "step": 1,
               "adjacent_reason": "", "category": "", "confidence": "High"}
    elif "any person" in excerpt or "every owner" in excerpt:
        obj = {"tier": "not", "unresolvable": "", "step": 2,
               "adjacent_reason": "", "category": "", "confidence": "Medium"}
    elif "tax" in excerpt and "levied" in excerpt:
        obj = {"tier": "adjacent", "unresolvable": "", "step": 4,
               "adjacent_reason": "revenue", "category": "other",
               "confidence": "Medium"}
    elif any(w in excerpt for w in ("license", "permit", "dealer", "business")):
        obj = {"tier": "core", "unresolvable": "", "step": 4,
               "adjacent_reason": "", "category": "entry", "confidence": "High"}
    else:
        obj = {"tier": "not", "unresolvable": "", "step": 2,
               "adjacent_reason": "", "category": "", "confidence": "Low"}
    if temperature > 0 and h % 7 == 0:          # jitter, so self-agreement < 1
        obj["tier"] = "adjacent" if obj["tier"] == "core" else obj["tier"]
        obj["adjacent_reason"] = "procedure" if obj["tier"] == "adjacent" else ""
        obj["category"] = obj["category"] or "other"
    obj["reasoning"] = "stub backend; no model was called."
    obj["notes"] = "stub"
    return json.dumps(obj)


def _post(url: str, payload: dict, headers: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return json.loads(fh.read().decode("utf-8"))


def call_openai(prompt: str, model: str, temperature: float) -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("OPENAI_API_KEY is not set (or use --backend stub)")
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    body = _post(f"{base}/chat/completions",
                 {"model": model, "temperature": temperature,
                  "messages": [{"role": "user", "content": prompt}]},
                 {"Authorization": f"Bearer {key}"})
    return body["choices"][0]["message"]["content"]


def call_anthropic(prompt: str, model: str, temperature: float) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY is not set (or use --backend stub)")
    body = _post("https://api.anthropic.com/v1/messages",
                 {"model": model, "temperature": temperature, "max_tokens": 1024,
                  "messages": [{"role": "user", "content": prompt}]},
                 {"x-api-key": key, "anthropic-version": "2023-06-01"})
    return "".join(b.get("text", "") for b in body.get("content", []))


BACKENDS = {"stub": call_stub, "openai": call_openai, "anthropic": call_anthropic}


def cached_call(prompt: str, backend: str, model: str, temperature: float,
                cache: pathlib.Path, retries: int = 3) -> str:
    key = hashlib.sha1(
        f"{backend}|{model}|{temperature}|{prompt}".encode("utf-8")).hexdigest()
    path = cache / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["response"]
    last = None
    for attempt in range(retries):
        try:
            resp = BACKENDS[backend](prompt, model, temperature)
            break
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last = exc
            time.sleep(2 ** attempt)
    else:
        raise SystemExit(f"model call failed after {retries} tries: {last}")
    path.write_text(json.dumps({"prompt": prompt, "response": resp}), encoding="utf-8")
    return resp


# --------------------------------------------------------------------- parsing

def parse(resp: str) -> dict | None:
    """Pull the JSON object out of a reply and normalize it to the schema.

    Returns None when nothing parses, which is recorded rather than retried into
    silence: a variant whose parse-failure rate is high is a finding about that
    prompt, not noise to be hidden.
    """
    txt = resp.strip()
    txt = re.sub(r"^```(?:json)?|```$", "", txt, flags=re.MULTILINE).strip()
    start, end = txt.find("{"), txt.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(txt[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None

    def pick(field, allowed):
        v = str(obj.get(field, "") or "").strip().lower()
        return v if v in allowed else ""

    out = {
        "tier": pick("tier", TIERS),
        "adjacent_reason": pick("adjacent_reason", REASONS),
        "category": pick("category", CATEGORIES),
        "unresolvable": pick("unresolvable", ["no-context", "truncated"]),
        "confidence": pick("confidence", ["high", "medium", "low"]),
        "reasoning": str(obj.get("reasoning", "") or "")[:600],
        "notes": str(obj.get("notes", "") or "")[:300],
    }
    try:
        out["step"] = int(obj.get("step"))
    except (TypeError, ValueError):
        out["step"] = ""
    # truncated is no longer a labeler value in v3; fold it to the live one.
    if out["unresolvable"] == "truncated":
        out["unresolvable"] = "no-context"
    if out["unresolvable"]:
        out["tier"] = ""
    if out["tier"] != "adjacent":
        out["adjacent_reason"] = ""
    return out


def outcome(rec: dict) -> str:
    """The 4-way coding the human merge uses: tier, or 'unresolvable'."""
    if rec.get("unresolvable"):
        return "unresolvable"
    return rec.get("tier") or ""


# ------------------------------------------------------------------------ gold

def labeler_name(path: pathlib.Path) -> str:
    stem = path.stem
    for prefix in ("round2_", "label_sheet_", "labels_"):
        if stem.startswith(prefix):
            stem = stem[len(prefix):]
    return (stem.split(" - ")[0].strip() or path.stem).lower()


OUTPUTS = {"round2_merged.csv", "round2_disagreements.csv",
           "round2_keyword_scores.csv", "round2_summary.txt",
           "llm_runs.csv", "llm_rowstats.csv"}


def load_round2(ldir: pathlib.Path) -> tuple[list, list]:
    """Rows with text and each human's 4-way outcome, plus the labeler names."""
    files = sorted(p for p in ldir.glob("round2_*.csv") if p.name not in OUTPUTS)
    if not files:
        raise SystemExit(f"no round-2 label files in {ldir.resolve()}")
    rows: dict[str, dict] = {}
    people = []
    for path in files:
        who = labeler_name(path)
        people.append(who)
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                cid = (r.get("chunk_id") or "").strip()
                if not cid:
                    continue
                rec = rows.setdefault(cid, {"chunk_id": cid, "human": {}})
                rec.setdefault("row_id", (r.get("row_id") or "").strip())
                rec.setdefault("header", (r.get("header") or "").strip())
                rec.setdefault("text", r.get("text") or "")
                tier = (r.get("tier") or "").strip().lower()
                unres = (r.get("unresolvable") or "").strip().lower()
                if tier and unres:          # self-contradiction: both cells drop
                    continue
                val = "unresolvable" if unres else (tier if tier in TIERS else "")
                if val:
                    rec["human"][who] = val
    out = sorted(rows.values(),
                 key=lambda r: int(r["row_id"]) if r["row_id"].isdigit() else 0)
    for r in out:
        vals = [r["human"][p] for p in sorted(people) if p in r["human"]]
        maj, uni = majority(vals) if vals else ("", False)
        r["gold"] = "" if maj == "tie" else maj
        r["unanimous"] = uni
        r["human_split"] = len(set(vals)) > 1
    return out, sorted(people)


def load_round1(ldir: pathlib.Path) -> list:
    """Round-1 sheets as a binary core-vs-rest proxy, for prompt development.

    Round 1 asked is_commerce yes/no/unsure, so this is a proxy and not the same
    question. Rows with any unsure are dropped rather than mapped.
    """
    files = sorted(ldir.glob("label_sheet_*.csv"))
    if not files:
        return []
    rows: dict[str, dict] = {}
    for path in files:
        who = labeler_name(path)
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                cid = (r.get("chunk_id") or "").strip()
                if not cid:
                    continue
                rec = rows.setdefault(cid, {"chunk_id": cid, "human": {}})
                rec.setdefault("row_id", (r.get("row_id") or "").strip())
                rec.setdefault("header", (r.get("header") or "").strip())
                rec.setdefault("text", r.get("text") or "")
                v = (r.get("is_commerce") or "").strip().lower()
                if v in ("yes", "no", "unsure"):
                    rec["human"][who] = v
    out = []
    for r in rows.values():
        vals = list(r["human"].values())
        if not vals or "unsure" in vals:
            continue
        maj, uni = majority(vals)
        r["gold"] = {"yes": "core", "no": "not"}.get(maj, "")
        r["unanimous"] = uni
        r["human_split"] = len(set(vals)) > 1
        if r["gold"]:
            out.append(r)
    return sorted(out, key=lambda r: int(r["row_id"]) if r["row_id"].isdigit() else 0)


# --------------------------------------------------------------------- scoring

def cohen_kappa(pairs: list[tuple[str, str]], categories: list[str]) -> float | None:
    """Two raters, same items. Fleiss on 2 raters is Cohen's up to rounding, but
    this is written out so the binary comparisons read plainly."""
    pairs = [(a, b) for a, b in pairs if a in categories and b in categories]
    n = len(pairs)
    if n < 2:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    pe = 0.0
    for c in categories:
        pa = sum(1 for a, _ in pairs if a == c) / n
        pb = sum(1 for _, b in pairs if b == c) / n
        pe += pa * pb
    if pe >= 1:
        return None
    return (po - pe) / (1 - pe)


def fmt(v) -> str:
    return "n/a" if v is None else f"{v:+.3f}"


def per_class(pairs: list[tuple[str, str]], label: str) -> tuple[float, float, float]:
    tp = sum(1 for g, m in pairs if g == label and m == label)
    fp = sum(1 for g, m in pairs if g != label and m == label)
    fn = sum(1 for g, m in pairs if g == label and m != label)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


# ------------------------------------------------------------------------ main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="labels")
    ap.add_argument("--prompts", default="prompts")
    ap.add_argument("--cache", default="out/llm_cache")
    ap.add_argument("--backend", default="stub", choices=sorted(BACKENDS))
    ap.add_argument("--model", default="stub-model")
    ap.add_argument("--temperature", type=float, default=0.7,
                    help="0 makes self-consistency meaningless; keep it above 0 "
                         "for the ambiguity-localization half")
    ap.add_argument("--repeats", type=int, default=3,
                    help="runs per row per variant, each with its own permutation")
    ap.add_argument("--variants", default="A,B,C,D,E")
    ap.add_argument("--eval", default="round2", choices=["round1", "round2"],
                    help="round1 is the development set (binary proxy); round2 is "
                         "the held-out evaluation")
    ap.add_argument("--split", type=float, default=0.0,
                    help="hold out this fraction of round 2 and score only it")
    ap.add_argument("--seed", type=int, default=71)
    ap.add_argument("--limit", type=int, default=0, help="first N rows, for a smoke test")
    ap.add_argument("--dry-run", action="store_true",
                    help="print one assembled prompt per variant and stop")
    args = ap.parse_args()

    ldir = pathlib.Path(args.labels)
    pdir = pathlib.Path(args.prompts)
    cache = pathlib.Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    frags = load_fragments(pdir)
    variants = [v.strip().upper() for v in args.variants.split(",") if v.strip()]
    for v in variants:
        if v not in VARIANTS:
            raise SystemExit(f"unknown variant {v!r}; known: {sorted(VARIANTS)}")

    if args.eval == "round1":
        rows = load_round1(ldir)
        if not rows:
            raise SystemExit(
                "no round-1 sheets (labels/label_sheet_*.csv) found. Use "
                "--eval round2 --split 0.33 to hold out part of round 2 instead.")
        label_space, binary = ["core", "not"], True
    else:
        rows, people = load_round2(ldir)
        label_space, binary = OUTCOMES, False
        if args.split > 0:
            rng = random.Random(args.seed)
            keep = rows[:]
            rng.shuffle(keep)
            n = max(1, int(len(keep) * args.split))
            held = {r["chunk_id"] for r in keep[:n]}
            rows = [r for r in rows if r["chunk_id"] in held]

    # Rows where the human majority tied have no gold answer to score against,
    # so they leave the evaluation. They are counted, not hidden: a tie is three
    # people failing to agree, which is a fact about the row.
    ties = [r["row_id"] for r in rows if not r.get("gold")]
    rows = [r for r in rows if r.get("gold")]
    if args.limit:
        rows = rows[:args.limit]
    if not rows:
        raise SystemExit("no rows with a gold label")

    if args.dry_run:
        rng = random.Random(args.seed)
        for v in variants:
            p = build_prompt(v, frags, rows[0]["text"], rows[0]["header"], rng)
            print("=" * 72)
            print(f"VARIANT {v}   {len(p)} chars, ~{len(p)//4} tokens")
            print("=" * 72)
            print(p)
        return

    # ---- run
    runs = []
    total = len(variants) * len(rows) * args.repeats
    done = 0
    for v in variants:
        for row in rows:
            for rep in range(args.repeats):
                rng = random.Random(args.seed * 1000 + rep)
                prompt = build_prompt(v, frags, row["text"], row["header"], rng)
                resp = cached_call(prompt, args.backend, args.model,
                                   args.temperature, cache)
                rec = parse(resp)
                runs.append({
                    "variant": v, "row_id": row["row_id"],
                    "chunk_id": row["chunk_id"], "repeat": rep,
                    "parsed": rec is not None,
                    "outcome": outcome(rec) if rec else "",
                    **({k: rec.get(k, "") for k in
                        ("tier", "adjacent_reason", "category", "unresolvable",
                         "step", "confidence", "reasoning", "notes")}
                       if rec else {}),
                })
                done += 1
                if done % 25 == 0 or done == total:
                    print(f"  {done}/{total}", file=sys.stderr)

    with (ldir / "llm_runs.csv").open("w", encoding="utf-8", newline="") as fh:
        cols = ["variant", "row_id", "chunk_id", "repeat", "parsed", "outcome",
                "tier", "adjacent_reason", "category", "unresolvable", "step",
                "confidence", "notes", "reasoning"]
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(runs)

    # ---- score
    lines: list[str] = []
    def say(s: str = "") -> None:
        lines.append(s)
        print(s)

    gold = {r["chunk_id"]: r["gold"] for r in rows}
    split = {r["chunk_id"]: r["human_split"] for r in rows}
    by = collections.defaultdict(list)
    for r in runs:
        by[(r["variant"], r["chunk_id"])].append(r)

    say(f"backend {args.backend}   model {args.model}   temp {args.temperature}"
        f"   repeats {args.repeats}")
    say(f"eval set {args.eval}"
        + (f" (held-out {args.split:.0%})" if args.split else "")
        + f"   rows {len(rows)}   label space {label_space}")
    if ties:
        say(f"excluded {len(ties)} rows with no human majority (tie): "
            + ", ".join(f"r{t}" for t in ties))
    if binary:
        say("round 1 is a yes/no proxy for core-vs-rest, not the same question;")
        say("use it to develop prompts, then evaluate once on round 2.")
    say()
    say("modal answer per row (ties broken by first), against human majority")
    say(f"  {'var':<4} {'acc':>6} {'kappa':>7} {'parse':>6} {'absten':>7}  per-class F1")

    summary = {}
    for v in variants:
        pairs, abst, parsed_n, n = [], 0, 0, 0
        for r in rows:
            recs = by[(v, r["chunk_id"])]
            n += len(recs)
            parsed_n += sum(1 for x in recs if x["parsed"])
            vals = [x["outcome"] for x in recs if x["outcome"]]
            if not vals:
                continue
            modal = collections.Counter(vals).most_common(1)[0][0]
            if modal == "unresolvable":
                abst += 1
            pairs.append((r["gold"], modal))
        acc = sum(1 for g, m in pairs if g == m) / len(pairs) if pairs else 0.0
        k = cohen_kappa(pairs, label_space)
        f1s = " ".join(f"{lab[:4]} {per_class(pairs, lab)[2]:.2f}"
                       for lab in label_space)
        summary[v] = (acc, k, pairs)
        say(f"  {v:<4} {acc:>6.3f} {fmt(k):>7} {parsed_n/n if n else 0:>6.0%}"
            f" {abst/len(rows):>7.0%}  {f1s}")

    say()
    say("contrasts (what each part of the codebook is worth)")
    def delta(a, b, why):
        if a in summary and b in summary:
            say(f"  {a} - {b}   acc {summary[a][0]-summary[b][0]:+.3f}"
                f"   {why}")
    delta("B", "A", "the four-step procedure")
    delta("C", "B", "reason codes with carve-outs")
    delta("D", "C", "edge-case log vs carve-out prose")
    delta("E", "C", "examples on top of full procedure")
    delta("E", "D", "procedure on top of examples")
    say("  human record for comparison: round 1 (definition only) kappa 0.232,")
    say("  round 2 (procedural) 0.549 all rows / 0.724 legible rows.")

    # ---- self-consistency and ambiguity localization
    say()
    say("self-consistency across repeats, and where it lines up with human splits")
    rowstats = []
    for v in variants:
        selfitems, unstable_split, unstable_agree = [], 0, 0
        stable_split, stable_agree = 0, 0
        for r in rows:
            vals = [x["outcome"] for x in by[(v, r["chunk_id"])] if x["outcome"]]
            if len(vals) < 2:
                continue
            selfitems.append(vals)
            unstable = len(set(vals)) > 1
            if unstable and split[r["chunk_id"]]:
                unstable_split += 1
            elif unstable:
                unstable_agree += 1
            elif split[r["chunk_id"]]:
                stable_split += 1
            else:
                stable_agree += 1
            rowstats.append({"variant": v, "row_id": r["row_id"],
                             "chunk_id": r["chunk_id"], "gold": r["gold"],
                             "model_modal": collections.Counter(vals).most_common(1)[0][0],
                             "model_unstable": int(unstable),
                             "human_split": int(split[r["chunk_id"]]),
                             "n_distinct": len(set(vals))})
        sk = fleiss_kappa(selfitems, label_space) if selfitems else None
        sa = gwet_ac1(selfitems, label_space) if selfitems else None
        tot = unstable_split + unstable_agree + stable_split + stable_agree
        p_split_given_unstable = (unstable_split / (unstable_split + unstable_agree)
                                  if unstable_split + unstable_agree else 0.0)
        p_split_overall = ((unstable_split + stable_split) / tot) if tot else 0.0
        say(f"  {v:<4} self-kappa {fmt(sk)}  AC1 {fmt(sa)}   "
            f"unstable rows {unstable_split + unstable_agree}/{tot}")
        say(f"       P(humans split | model unstable) {p_split_given_unstable:.2f}"
            f"   vs base rate {p_split_overall:.2f}")

    with (ldir / "llm_rowstats.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["variant", "row_id", "chunk_id", "gold",
                                           "model_modal", "model_unstable",
                                           "human_split", "n_distinct"])
        w.writeheader()
        w.writerows(rowstats)

    say()
    say("  A lift over the base rate is the ambiguity-localization result: the")
    say("  rows a model cannot answer the same way twice are the rows the")
    say("  codebook under-specifies, and that detector runs without humans.")

    if args.eval == "round2" and not args.split:
        say()
        say("model as a declared fourth annotator (variant E modal answer)")
        if "E" in summary:
            rows2, people = load_round2(ldir)
            idx = {r["chunk_id"]: r for r in rows}
            four = []
            for r in rows2:
                if r["chunk_id"] not in idx:
                    continue
                vals = [x["outcome"] for x in by[("E", r["chunk_id"])] if x["outcome"]]
                if not vals or len(r["human"]) < len(people):
                    continue
                modal = collections.Counter(vals).most_common(1)[0][0]
                four.append([r["human"][p] for p in people] + [modal])
            if four:
                say(f"  4-way Fleiss with model   {fmt(fleiss_kappa(four, OUTCOMES))}"
                    f"   AC1 {fmt(gwet_ac1(four, OUTCOMES))}   (n={len(four)})")
                say(f"  humans only               "
                    f"{fmt(fleiss_kappa([x[:-1] for x in four], OUTCOMES))}")
                for i, p in enumerate(people):
                    say(f"  model vs {p:<8}         "
                        f"{fmt(cohen_kappa([(x[i], x[-1]) for x in four], OUTCOMES))}")

    say()
    say(f"wrote {ldir/'llm_runs.csv'}, {ldir/'llm_rowstats.csv'}, "
        f"{ldir/'llm_ablation.txt'}")
    (ldir / "llm_ablation.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
