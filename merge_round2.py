"""Merge the round-2 label sheets from labels/ and report where we disagree.

Round 2 replaced round 1's single is_commerce/category pair with the three tiers
and the decision procedure in definition_v2.md, so merge_labels.py cannot read
these sheets: the coded columns are tier, adjacent_reason, category,
unresolvable and step.

    python merge_round2.py

What it does:

    joins labels/round2_<name>.csv on chunk_id
    majority vote on tier, adjacent_reason and category
    lists the rows we did not agree on, most contested first
    reports Fleiss' kappa and Gwet's AC1 per field, leading with the figure over
      every row - tier and unresolvable together, since an unresolvable call is
      an answer step 1 asks for, not a missing label
    reports the same agreement again with the `truncated` rows dropped, to separate
      disagreement about LOCUS chunk boundaries from disagreement about our wording
    breaks the tier call down by stratum, and scores keywords, when the key is present
    runs the consistency checks definition_v2.md implies (adjacent needs a reason,
    unresolvable means no tier)

Outputs, in labels/:

    round2_merged.csv          one row per chunk: each labeler's call, majority, agreement
    round2_disagreements.csv   the subset worth talking through
    round2_summary.txt         the printed report, so a round is committable as a number
    round2_keyword_scores.csv  per keyword: rows labeled, share called core (needs --key)

Two statistics, not one. Fleiss' kappa is what round 1 reported (0.232 on
is_commerce), so it is what round 2 is compared against. But kappa collapses
toward zero when one category dominates, and in a stratified sheet that is a
property of the sample rather than of the labelers. Gwet's AC1 does not have
that behaviour, so a large kappa/AC1 gap is itself the finding: it says the
labelers agree but the sheet is lopsided. Both are printed, always.

A labeler who coded both `tier` and `unresolvable` on one row has contradicted
step 1, and both cells are dropped from the statistics rather than one being
preferred. They survive in merged.csv with an `excluded` column naming who.

The dropdowns in make_sheets.py mean the coded cells should already be clean.
Anything off-list is still reported rather than dropped - a value that escaped a
dropdown means someone typed around the validation, and that is worth seeing.
"""

import argparse
import collections
import csv
import pathlib

from merge_labels import fleiss_kappa, majority

# Must match make_sheets.py, which must match definition_v2.md.
TIERS = ["core", "adjacent", "not"]
ADJACENT_REASONS = ["gov-market", "revenue", "land-use", "general-law",
                    "counterparty", "procedure", "definition", "sometimes-business"]
CATEGORIES = ["entry", "operation", "exit", "other"]
UNRESOLVABLE = ["truncated", "no-context"]
STEPS = ["1", "2", "3", "4", "5"]

# Sensitivity analysis on the procedure's own granularity, not on the labels.
#
# Round 2 gave step kappa 0.440 against tier kappa 0.724: the group reaches the
# same tier along different routes. The suspected cause is that steps 2 and 3 are
# not distinguished in practice. Both terminate in `not`, and the question they
# ask is close - step 2 is "is any commercial subject named at all", step 3 is
# "a commercial subject is named, but would a non-commercial actor doing the same
# thing be bound anyway". A labeler who reads "any person" as settling the matter
# can record either number for the same judgment. Sachin resolved 26 rows at
# step 2 and 2 at step 3; daniel resolved 10 and 17. If those are largely the
# same rows, step kappa is measuring vocabulary rather than disagreement.
#
# Step 4 is the other candidate: it fired twice in 225 labeler-rows, and its only
# outcome is `adjacent / counterparty`, which step 5 could select as a reason
# code without a gate of its own.
#
# Collapsing categories is not a free win. Merging two values raises observed
# agreement mechanically, but it also raises Fleiss' chance term, so kappa can
# move either way - which is what makes the comparison informative rather than
# decorative. Report the ladder, never a collapsed figure on its own.
STEP_COLLAPSES = [
    ("2+3 merged", {"2": "2/3", "3": "2/3"}),
    ("2+3 and 4+5 merged", {"2": "2/3", "3": "2/3", "4": "4/5", "5": "4/5"}),
    ("4+5 merged only", {"4": "4/5", "5": "4/5"}),
]

CODED = {"tier": TIERS, "adjacent_reason": ADJACENT_REASONS,
         "category": CATEGORIES, "unresolvable": UNRESOLVABLE, "step": STEPS}

OUTPUTS = {"round2_merged.csv", "round2_disagreements.csv",
           "round2_keyword_scores.csv", "round2_summary.txt"}

KEY_FIELDS = ["slice", "topic", "function", "matched", "state", "city", "county"]


def norm(field: str, raw: str) -> tuple[str | None, str | None]:
    """Normalize one coded cell. Returns (value, offlist_raw).

    Blank is ignored rather than counted as a judgment, and for `tier` a blank
    is usually not unfinished work: step 1 of the decision procedure says to set
    `unresolvable` and leave `tier` empty when the chunk never names what it
    governs. All 35 untiered cells in the first three sheets carried an
    `unresolvable` code, so they are answers, not gaps - which is why the report
    leads with the figure that keeps them (tier + unresolvable, n = all rows) and
    treats the tier-only figure as conditional on the chunk being legible.
    A truly empty cell with no `unresolvable` code is unfinished, and the
    per-labeler `tiered x/y` counts are where that shows up.
    """
    v = (raw or "").strip().lower()
    if not v:
        return None, None
    if v in CODED[field]:
        return v, None
    return None, (raw or "").strip()


def labeler_name(path: pathlib.Path) -> str:
    """One identity per FILE, as in merge_labels.py: the column can drift, the
    file cannot. round2_sachin.csv -> sachin."""
    stem = path.stem
    for prefix in ("round2_", "label_sheet_", "labels_"):
        if stem.startswith(prefix):
            stem = stem[len(prefix):]
    return (stem.split(" - ")[0].strip() or path.stem).lower()


def gwet_ac1(items: list[list[str]], categories: list[str]) -> float | None:
    """Gwet's AC1. Same inputs as fleiss_kappa.

    Identical observed agreement; the chance term is
    (1/(k-1)) * sum_j pi_j (1 - pi_j), which does not blow up when one category
    takes almost every rating the way Fleiss' sum of squared marginals does.
    """
    items = [i for i in items if len(i) == len(items[0])] if items else []
    n = len(items[0]) if items else 0
    if not items or n < 2:
        return None
    k = len(categories)
    if k < 2:
        return None
    idx = {c: j for j, c in enumerate(categories)}
    N = len(items)

    pi = [0.0] * k
    agree = []
    for ratings in items:
        counts = [0] * k
        for r in ratings:
            counts[idx[r]] += 1
        for j in range(k):
            pi[j] += counts[j]
        agree.append((sum(c * c for c in counts) - n) / (n * (n - 1)))
    pi = [v / (N * n) for v in pi]
    p_a = sum(agree) / N
    p_e = sum(p * (1 - p) for p in pi) / (k - 1)
    if p_e >= 1:
        return None
    return (p_a - p_e) / (1 - p_e)


def collapse(items: list[list[str]], mapping: dict[str, str],
             categories: list[str]) -> tuple[list[list[str]], list[str]]:
    """Apply a value mapping to every rating, returning the new items and the
    new category list in a stable order. Values absent from the mapping pass
    through unchanged."""
    out = [[mapping.get(v, v) for v in row] for row in items]
    seen: list[str] = []
    for c in categories:
        m = mapping.get(c, c)
        if m not in seen:
            seen.append(m)
    return out, seen


def unanimous_rows(items: list[list[str]]) -> int:
    """How many rows every labeler rated identically."""
    return sum(1 for row in items if len(set(row)) == 1)


def both(items: list[list[str]], categories: list[str]) -> str:
    """Kappa and AC1 side by side, for the report."""
    if not items:
        return f"n=0"
    k = fleiss_kappa(items, categories)
    a = gwet_ac1(items, categories)
    ks = "n/a" if k is None else f"{k:+.3f}"
    as_ = "n/a" if a is None else f"{a:+.3f}"
    return f"kappa {ks}   AC1 {as_}   (n={len(items)})"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="labels")
    ap.add_argument("--key", default="out/round2_key.csv",
                    help="coordinator-only key: adds stratum, state and keyword "
                         "columns the sheets withheld. Skipped if missing.")
    args = ap.parse_args()

    ldir = pathlib.Path(args.labels)
    files = sorted(p for p in ldir.glob("round2_*.csv") if p.name not in OUTPUTS)
    if not files:
        raise SystemExit(f"no round-2 label files in {ldir.resolve()} "
                         f"(expected labels/round2_<name>.csv)")

    key: dict[str, dict] = {}
    kpath = pathlib.Path(args.key)
    if kpath.exists():
        with kpath.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                key[(row.get("chunk_id") or "").strip()] = row

    rows: dict[str, dict] = {}
    labelers: set[str] = set()
    offlist: list[tuple[str, str, str, str]] = []     # labeler, row_id, field, raw
    seen_rows: dict[str, int] = {}                    # labeler -> rows in their file

    for path in files:
        who = labeler_name(path)
        labelers.add(who)
        with path.open(encoding="utf-8-sig", newline="") as fh:
            n = 0
            for row in csv.DictReader(fh):
                cid = (row.get("chunk_id") or "").strip()
                if not cid:
                    continue
                n += 1
                rec = rows.setdefault(cid, {"meta": {}, "notes": [],
                                            **{f: {} for f in CODED}})
                rec["meta"].setdefault("row_id", (row.get("row_id") or "").strip())
                rec["meta"].setdefault("header", (row.get("header") or "")[:120])
                rec["meta"].setdefault("text_truncated",
                                       (row.get("text_truncated") or "").strip())
                note = (row.get("notes") or "").strip()
                if note:
                    rec["notes"].append(f"{who}: {note}")
                for field in CODED:
                    val, bad = norm(field, row.get(field, ""))
                    if val:
                        rec[field][who] = val
                    if bad:
                        offlist.append((who, rec["meta"]["row_id"], field, bad))
            seen_rows[who] = n

    people = sorted(labelers)

    # A labeler who set both `tier` and `unresolvable` on one row has given two
    # answers that cannot both hold: step 1 says an unresolvable chunk gets no
    # tier. Neither cell can be trusted over the other, so both leave the
    # statistics - counting one would be us picking their answer for them. The
    # raw values stay in merged.csv, and `excluded` names whose cells were cut,
    # so the row can be read and sent back for a real answer.
    selfcontra: list[tuple[str, str]] = []
    for cid, rec in rows.items():
        rec["raw"] = {}
        rec["excluded"] = []
        for p in people:
            if p in rec["tier"] and p in rec["unresolvable"]:
                selfcontra.append((p, rec["meta"].get("row_id", "")))
                rec["raw"][("tier", p)] = rec["tier"].pop(p)
                rec["raw"][("unresolvable", p)] = rec["unresolvable"].pop(p)
                rec["excluded"].append(p)

    for cid, rec in rows.items():
        k = key.get(cid, {})
        for f in KEY_FIELDS:
            rec["meta"][f] = (k.get(f) or "").strip()

    # ---- merged.csv -------------------------------------------------------
    fields = (["row_id", "chunk_id"] + (KEY_FIELDS if key else [])
              + ["header", "text_truncated"]
              + [f"{f}_{p}" for f in ("tier", "adjacent_reason", "category", "step",
                                      "unresolvable") for p in people]
              + ["tier_majority", "tier_unanimous", "reason_majority",
                 "reason_unanimous", "category_majority", "category_unanimous",
                 "n_tier", "excluded", "notes"])

    out_rows = []
    for cid, rec in rows.items():
        tvals = [rec["tier"][p] for p in people if p in rec["tier"]]
        rvals = [rec["adjacent_reason"][p] for p in people if p in rec["adjacent_reason"]]
        gvals = [rec["category"][p] for p in people if p in rec["category"]]
        tmaj, tuni = majority(tvals) if tvals else ("", False)
        rmaj, runi = majority(rvals) if rvals else ("", False)
        gmaj, guni = majority(gvals) if gvals else ("", False)
        out_rows.append({
            "row_id": rec["meta"].get("row_id", ""), "chunk_id": cid,
            **({f: rec["meta"].get(f, "") for f in KEY_FIELDS} if key else {}),
            "header": rec["meta"].get("header", ""),
            "text_truncated": rec["meta"].get("text_truncated", ""),
            **{f"{f}_{p}": rec[f].get(p, "") or rec["raw"].get((f, p), "")
               for f in ("tier", "adjacent_reason", "category", "step", "unresolvable")
               for p in people},
            "tier_majority": tmaj, "tier_unanimous": tuni,
            "reason_majority": rmaj, "reason_unanimous": runi,
            "category_majority": gmaj, "category_unanimous": guni,
            "n_tier": len(tvals), "excluded": ",".join(rec["excluded"]),
            "notes": " | ".join(rec["notes"]),
        })
    out_rows.sort(key=lambda r: int(r["row_id"]) if r["row_id"].isdigit() else 0)

    merged_path = ldir / "round2_merged.csv"
    with merged_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    # Contested = everyone who labelled the tier did not land on the same one.
    # A row two people called core and one left blank is not a disagreement.
    contested = [r for r in out_rows if r["n_tier"] >= 2 and not r["tier_unanimous"]]
    # Tier agreed but the adjacent reason did not: a different, finer argument.
    reason_split = [r for r in out_rows
                    if r["tier_unanimous"] and r["tier_majority"] == "adjacent"
                    and r["reason_majority"] and not r["reason_unanimous"]]
    dis_path = ldir / "round2_disagreements.csv"
    with dis_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(contested + [r for r in reason_split if r not in contested])

    # ---- agreement --------------------------------------------------------
    def complete(field: str) -> list[list[str]]:
        """Ratings for the rows every labeler coded, in a fixed labeler order."""
        if len(people) < 2:
            return []
        return [[rec[field][p] for p in people] for rec in rows.values()
                if all(p in rec[field] for p in people)]

    tier_items = complete("tier")
    # Binary collapse. Round 1's is_commerce was a yes/no question, and core vs
    # (adjacent or not) is the closest round-2 equivalent. Still not like for
    # like: round 2 is a different sample, held out round 1's chunks, and this
    # subset conditions on legibility.
    bin_items = [["core" if v == "core" else "rest" for v in i] for i in tier_items]
    # tier + unresolvable as a 4th value. This is the primary figure: an
    # unresolvable call is a judgment the procedure asks for, so a row where one
    # person said core and another said unresolvable is a real disagreement, and
    # dropping it would score the group on the subset where it already agreed the
    # chunk was readable. The gap between this and the tier-only figure is the
    # size of the step-1 problem.
    four = []
    for rec in rows.values():
        row = []
        for p in people:
            if p in rec["tier"]:
                row.append(rec["tier"][p])
            elif p in rec["unresolvable"]:
                row.append("unresolvable")
            else:
                row = []
                break
        if row:
            four.append(row)
    # Same 4-way coding, minus every row anyone called `truncated`. Step 1 bundles
    # two different stopping conditions - the chunk is cut off mid-provision, and
    # the chunk never names what it governs - and only the first is a property of
    # LOCUS chunking rather than of the definition. Dropping those rows says how
    # much of the step-1 disagreement is chunking and how much is wording we own.
    no_trunc = []
    for rec in rows.values():
        if any(rec["unresolvable"].get(p) == "truncated" for p in people):
            continue
        row = [rec["tier"].get(p) or ("unresolvable" if p in rec["unresolvable"] else "")
               for p in people]
        if all(row):
            no_trunc.append(row)

    reason_items = complete("adjacent_reason")
    cat_items = complete("category")
    step_items = complete("step")

    # Rows where every labeler recorded both an outcome (tier or unresolvable)
    # and a step, paired so the two can be read against each other. The question
    # this answers: when the group lands on the same answer, how often does it
    # claim to have got there by different routes? That count is the size of the
    # vocabulary problem, as distinct from real disagreement.
    paired: list[tuple[list[str], list[str]]] = []
    for rec in rows.values():
        outcome, steps = [], []
        for p in people:
            if p in rec["tier"]:
                outcome.append(rec["tier"][p])
            elif p in rec["unresolvable"]:
                outcome.append("unresolvable")
            else:
                outcome = []
                break
            if p in rec["step"]:
                steps.append(rec["step"][p])
            else:
                outcome = []
                break
        if outcome and len(steps) == len(people):
            paired.append((outcome, steps))
    same_answer = [s for o, s in paired if len(set(o)) == 1]

    # ---- consistency checks ----------------------------------------------
    checks = collections.Counter()
    detail: dict[str, list[str]] = collections.defaultdict(list)
    for r in out_rows:
        for p in people:
            tier, reason = r[f"tier_{p}"], r[f"adjacent_reason_{p}"]
            unres, step = r[f"unresolvable_{p}"], r[f"step_{p}"]
            if tier == "adjacent" and not reason:
                checks["adjacent with no reason"] += 1
                detail["adjacent with no reason"].append(f"{p} r{r['row_id']}")
            if tier != "adjacent" and reason:
                checks["reason given but tier is not adjacent"] += 1
                detail["reason given but tier is not adjacent"].append(f"{p} r{r['row_id']}")
            if tier == "core" and not r[f"category_{p}"]:
                checks["core with no category"] += 1
                detail["core with no category"].append(f"{p} r{r['row_id']}")
            if tier and not step:
                checks["tier with no step"] += 1
                detail["tier with no step"].append(f"{p} r{r['row_id']}")

    # ---- keyword scores ---------------------------------------------------
    kw_path = ldir / "round2_keyword_scores.csv"
    if key:
        hits, core_hits = collections.Counter(), collections.Counter()
        for r in out_rows:
            if not r.get("matched") or not r["tier_majority"]:
                continue
            for kw in [x.strip() for x in r["matched"].split(";") if x.strip()]:
                hits[kw] += 1
                if r["tier_majority"] == "core":
                    core_hits[kw] += 1
        with kw_path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["keyword", "rows_labeled", "called_core", "share_core"])
            for kw, n in hits.most_common():
                w.writerow([kw, n, core_hits[kw], round(core_hits[kw] / n, 3)])

    # ---- report -----------------------------------------------------------
    lines: list[str] = []
    def say(s: str = "") -> None:
        lines.append(s)
        print(s)

    say(f"label files      {len(files)}  ({', '.join(people)})")
    say(f"rows seen        {len(rows)}   key {'joined' if key else 'ABSENT - no strata or keywords'}")
    say(f"rows all coded   {len(four)} (tier or unresolvable)   all tiered {len(tier_items)}")
    say(f"disagreements    {len(contested)} on tier, {len(reason_split)} on reason only"
        f"  -> {dis_path}")
    say()
    say("agreement, over rows every labeler coded")
    say(f"  PRIMARY        {both(four, TIERS + ['unresolvable'])}")
    say( "                 tier + unresolvable together; only self-contradicting cells dropped")
    say(f"  minus trunc    {both(no_trunc, TIERS + ['unresolvable'])}")
    say( "                 rows anyone called truncated dropped: LOCUS chunking, not our wording")
    say( "  conditional on all three finding the chunk legible:")
    say(f"    tier 3-way   {both(tier_items, TIERS)}")
    say(f"    core vs rest {both(bin_items, ['core', 'rest'])}   <- nearest thing to round 1's 0.232")
    say(f"  adjacent_rsn   {both(reason_items, ADJACENT_REASONS)}")
    say(f"  category       {both(cat_items, CATEGORIES)}")
    say(f"  step           {both(step_items, STEPS)}")
    say()
    say("step agreement under collapsed codings (sensitivity on the procedure, not the labels)")
    say(f"  as recorded          {both(step_items, STEPS)}   unanimous "
        f"{unanimous_rows(step_items)}/{len(step_items)}")
    for label, mapping in STEP_COLLAPSES:
        ci, cc = collapse(step_items, mapping, STEPS)
        say(f"  {label:<20} {both(ci, cc)}   unanimous "
            f"{unanimous_rows(ci)}/{len(ci)}")
    say( "  merging values raises raw agreement AND the chance term, so kappa can fall")
    say()
    say("same answer, different route")
    say(f"  rows all three answered identically (tier or unresolvable)   {len(same_answer)}"
        f"/{len(paired)}")
    for label, mapping in [("as recorded", {})] + STEP_COLLAPSES:
        ci, _ = collapse(same_answer, mapping, STEPS)
        split = len(ci) - unanimous_rows(ci)
        say(f"    {label:<20} same tier, different step: {split:>3}"
            + ("   <- route-only disagreement" if not mapping else ""))
    say()
    say("tier by labeler (the spread is itself the finding)")
    for p in people:
        c = collections.Counter(rec["tier"][p] for rec in rows.values() if p in rec["tier"])
        u = sum(1 for rec in rows.values() if p in rec["unresolvable"])
        tot = sum(c.values())
        pct = (lambda n: f"{100*n/tot:.0f}%" if tot else "-")
        say(f"  {p:<8} core {c['core']:>3} ({pct(c['core'])})  adjacent {c['adjacent']:>3} "
            f"({pct(c['adjacent'])})  not {c['not']:>3} ({pct(c['not'])})  "
            f"unres {u:>2}  tiered {tot}/{seen_rows.get(p, 0)}")
    say()
    say("step that decided it (where the procedure is actually doing work)")
    for p in people:
        c = collections.Counter(rec["step"][p] for rec in rows.values() if p in rec["step"])
        say(f"  {p:<8} " + "  ".join(f"s{s} {c[s]:>2}" for s in STEPS))
    say()
    say("adjacent reasons, majority call")
    rc = collections.Counter(r["reason_majority"] for r in out_rows
                             if r["tier_majority"] == "adjacent" and r["reason_majority"])
    if rc:
        for code, n in rc.most_common():
            say(f"  {code:<20} {n}")
    else:
        say("  none")
    if key:
        say()
        say("tier by stratum, majority call")
        strata = collections.defaultdict(collections.Counter)
        for r in out_rows:
            if r["tier_majority"]:
                strata[r["slice"] or "?"][r["tier_majority"]] += 1
        for s in sorted(strata):
            c = strata[s]
            tot = sum(c.values())
            say(f"  {s:<10} core {c['core']:>3}/{tot}  adjacent {c['adjacent']:>3}  "
                f"not {c['not']:>3}  tie {c['tie']:>2}")
    if offlist:
        say()
        say(f"off-list values  {len(offlist)}  (typed around a dropdown; ignored in the stats)")
        for who, rid, field, raw in offlist[:15]:
            say(f"  {who:<8} r{rid:<4} {field:<16} {raw!r}")
        if len(offlist) > 15:
            say(f"  ... {len(offlist) - 15} more")
    say()
    say("consistency checks, per labeler-row")
    if selfcontra:
        say(f"  {'unresolvable AND a tier':<36} {len(selfcontra):>3}   "
            + ", ".join(f"{w} r{r}" for w, r in selfcontra)
            + "   <- both cells dropped from every statistic")
    if checks or selfcontra:
        for name, n in checks.most_common():
            say(f"  {name:<36} {n:>3}   {', '.join(detail[name][:8])}"
                + (" ..." if len(detail[name]) > 8 else ""))
    else:
        say("  all clean")
    say()
    outs = [merged_path, dis_path, ldir / 'round2_summary.txt'] + ([kw_path] if key else [])
    say("wrote            " + ", ".join(str(p) for p in outs))

    (ldir / "round2_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
