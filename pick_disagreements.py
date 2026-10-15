"""Rank the contested rows by how far apart we actually were, for the discussion.

labels/disagreements.csv is sorted only by two booleans, so a row where one
person said unsure sits next to a row where two people flatly contradicted each
other. This scores the gap instead, and writes the top rows with the text
attached so a meeting can run off the one file.

    python pick_disagreements.py --top 20

Score, per row:

    commerce   yes and no both present      3.0   flat contradiction
               everyone unsure              2.0   definition gives no answer
               yes-or-no plus unsure        1.5   one person could not call it
    category   three distinct answers       2.0
               two distinct answers         1.0
               blank while calling it
                 commerce                   0.5   no category fit
    boundary   row is in the boundary slice 0.5   the slice built to be argued about

Raw score alone makes for a monotonous meeting: ten near-identical "two of us
said no, one said yes" inspection rows crowd out everything else. So the queue is
filled round-robin over themes, at most --per-theme rows each, and every row
carries the open question in definition.md it bears on. Ties break toward rows
with notes, since a written reason is what turns into a definition edit.
"""
import argparse, collections, csv, pathlib, re, sys

PEOPLE = ("ainesh", "daniel", "sachin")

# theme -> (pattern over matched keywords + header + topic, open question it tests)
THEMES = [
    ("fees", r"\bfee\b|\bfees\b|application fee",
     "Q1 fees vs penalties"),
    ("tax", r"\btax|occupation tax|revenue measure",
     "Q2 is taxation commerce regulation?"),
    ("home/rental", r"home occupation|short.?term rental|bed and breakfast|lodging|hotel|motel",
     "Q3 commerce inside a residence"),
    ("signs", r"\bsigns?\b|signage|sign board|billboard",
     "Q4 signs as commercial speech"),
    ("franchise/gov-market", r"franchis|utilit|cable|telecom|competitive bid|procurement|purchasing",
     "Q5 government as a market actor"),
    ("sometimes-a-business", r"kennel|day care|daycare|massage|towing|\bdog|animal|peddl|solicit",
     "Q6 activity is a business only sometimes"),
    ("definitions/procedure", r"definition|procedure|hearing|\bnotice\b|schedule|exemption|applicab",
     "Q7 definitions and procedure: substantive or not?"),
    ("nuisance/general-law", r"noise|nuisance|odor|litter|intoxicat|minor",
     "working definition: does it bind businesses as businesses?"),
    ("inspection", r"inspect|maintenance and reporting",
     "operation scope: inspection of commercial premises"),
    ("zoning", r"zoning|permitted use|occupancy|height regulation",
     "Q3/Q4 zoning carries commerce LOCUS files elsewhere"),
    ("licensing", r"licens|permit|renewal|revocat|suspen|registrat",
     "entry/exit scope"),
]


def theme_of(row):
    hay = " ".join([row.get("matched", ""), row.get("header", ""),
                    row.get("topic", "")]).lower()
    for name, pattern, question in THEMES:
        if re.search(pattern, hay):
            return name, question
    fallback = (row.get("topic") or "").strip() or (row.get("function") or "").strip()
    return f"topic:{(fallback or 'unclassified').lower()}", "no open question maps yet"


def score(row, people):
    calls = [c for c in (row.get(f"{p}_commerce", "").strip() for p in people) if c]
    cats = [row.get(f"{p}_category", "").strip() for p in people]

    reasons, s = [], 0.0

    if "yes" in calls and "no" in calls:
        s += 3.0
        reasons.append("yes vs no")
    elif calls and all(c == "unsure" for c in calls):
        s += 2.0
        reasons.append("all unsure")
    elif "unsure" in calls and ({"yes", "no"} & set(calls)):
        s += 1.5
        reasons.append("unsure vs called")

    distinct = {c for c in cats if c}
    if len(distinct) >= 3:
        s += 2.0
        reasons.append("3 categories")
    elif len(distinct) == 2:
        s += 1.0
        reasons.append("2 categories")
    if any(not c for c in cats) and "yes" in calls:
        s += 0.5
        reasons.append("no category given")

    if row.get("slice") == "boundary":
        s += 0.5
        reasons.append("boundary slice")

    return s, "; ".join(reasons)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="labels/round1_clean.csv")
    ap.add_argument("--out", default="labels/discussion_queue.csv")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--per-theme", type=int, default=2,
                    help="most rows one theme may contribute; 0 lifts the cap")
    ap.add_argument("--chars", type=int, default=700,
                    help="how much section text to carry into the sheet")
    args = ap.parse_args()

    src = pathlib.Path(args.src)
    if not src.exists():
        sys.exit(f"{src} not found; run clean_round1.py first")

    with src.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"{src} is empty")

    people = [p for p in PEOPLE if f"{p}_commerce" in rows[0]]

    scored = []
    for r in rows:
        s, why = score(r, people)
        if s <= 0:
            continue
        notes = [f"{p}: {r.get(f'{p}_notes', '').strip()}"
                 for p in people if r.get(f"{p}_notes", "").strip()]
        theme, question = theme_of(r)
        scored.append((s, bool(notes), {
            "rank": 0,
            "gap_score": s,
            "theme": theme,
            "open_question": question,
            "why_contested": why,
            "chunk_id": r["chunk_id"],
            "slice": r.get("slice", ""),
            "state": r.get("state", ""),
            "function": r.get("function", ""),
            "topic": r.get("topic", ""),
            "matched": r.get("matched", ""),
            "header": r.get("header", ""),
            **{f"{p}_commerce": r.get(f"{p}_commerce", "") for p in people},
            **{f"{p}_category": r.get(f"{p}_category", "") for p in people},
            "notes": " || ".join(notes),
            "text": " ".join((r.get("content_first_2000") or "").split())[:args.chars],
        }))

    scored.sort(key=lambda t: (-t[0], not t[1]))

    if args.per_theme:
        by_theme = collections.OrderedDict()
        for _, _, d in scored:
            by_theme.setdefault(d["theme"], []).append(d)
        picked = []
        for depth in range(args.per_theme):
            for items in by_theme.values():
                if len(items) > depth:
                    picked.append(items[depth])
            if len(picked) >= args.top:
                break
        picked.sort(key=lambda d: -d["gap_score"])
        picked = picked[:args.top]
    else:
        picked = [d for _, _, d in scored[:args.top]]

    for i, d in enumerate(picked, 1):
        d["rank"] = i

    out = pathlib.Path(args.out)
    out.parent.mkdir(exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(picked[0].keys()))
        w.writeheader()
        w.writerows(picked)

    print(f"contested rows   {len(scored)} of {len(rows)}")
    print(f"themes seen      {len({d['theme'] for _, _, d in scored})}")
    print(f"written          {len(picked)}  -> {out}")
    print()
    for d in picked:
        calls = "/".join(d.get(f"{p}_commerce") or "-" for p in people)
        print(f"{d['rank']:>3}. {d['gap_score']:>4}  {calls:<18} {d['theme']:<22} {d['header'][:52]}")
        print(f"       {d['why_contested']}  ->  {d['open_question']}")


if __name__ == "__main__":
    main()
