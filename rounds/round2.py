"""Round 2's merge: three tiers, the decision procedure, the reason codes.

Reads the sheets collected under codebook v2, which is why the schema version
is pinned to 2 here: round 2 allowed `truncated` as an `unresolvable` value and
numbered the steps 1-5. Codebook v3 removed the first and merged steps 2 and 3,
so a round-3 merge will pin version 3 instead.

    python merge_round.py --round 2

A labeler who coded both `tier` and `unresolvable` on one row has contradicted
step 1, and both cells are dropped rather than one being preferred.
"""

import collections
import csv
import pathlib

from wp3 import agreement, schema
from wp3.agreement import both, collapse, fleiss_kappa, gwet_ac1, majority, unanimous_rows
from wp3.sheets import labeler_name, sheet_files

SCHEMA_VERSION = 2
CODED = schema.coded_columns(SCHEMA_VERSION)
TIERS = schema.TIERS
ADJACENT_REASONS = schema.ADJACENT_REASONS
CATEGORIES = schema.CATEGORIES
UNRESOLVABLE = schema.unresolvable_values(SCHEMA_VERSION)
STEPS = schema.steps(SCHEMA_VERSION)
KEY_FIELDS = ["slice", "topic", "function", "matched", "state", "city", "county"]


STEP_COLLAPSES = [
    ("2+3 merged", {"2": "2/3", "3": "2/3"}),
    ("2+3 and 4+5 merged", {"2": "2/3", "3": "2/3", "4": "4/5", "5": "4/5"}),
    ("4+5 merged only", {"4": "4/5", "5": "4/5"}),
]


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

def merge(ldir: pathlib.Path, outdir: pathlib.Path, key_path: pathlib.Path | None) -> None:
    files = sheet_files(ldir, 2)
    if not files:
        raise SystemExit(f"no round-2 label files in {ldir.resolve()} "
                         f"(expected labels/round2_<name>.csv)")

    key: dict[str, dict] = {}
    kpath = key_path if key_path else pathlib.Path("out/round2_key.csv")
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

    merged_path = outdir / "round2_merged.csv"
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
    dis_path = outdir / "round2_disagreements.csv"
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
    kw_path = outdir / "round2_keyword_scores.csv"
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
    outs = [merged_path, dis_path, outdir / 'round2_summary.txt'] + ([kw_path] if key else [])
    say("wrote            " + ", ".join(str(p) for p in outs))

    (outdir / "round2_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

