"""Merge the label sheets from labels/ and report where we disagree.

Each labeler works in their own copy of out/label_sheet.csv and hands it back.
Drop those files in labels/ named label_sheet_<name>.csv, then:

    python merge_labels.py

What it does:

    joins every labels/*.csv on chunk_id
    takes a majority vote on is_commerce and category
    lists the rows we did not agree on
    reports Fleiss' kappa per field, over rows every labeler covered
    scores each keyword by the share of its hits the group called commerce

Outputs, in labels/:

    merged.csv           one row per chunk: each labeler's call, the majority, agreement
    disagreements.csv    the subset worth talking through, most contested first
    keyword_scores.csv   per keyword: hits labeled, share called commerce

Accepted values for is_commerce: yes/y/true/1, no/n/false/0, unsure/u/maybe/?.
Blank means not labeled and is ignored rather than counted as a no.
"""

import argparse
import collections
import csv
import pathlib

YES = {"yes", "y", "true", "1", "t"}
NO = {"no", "n", "false", "0", "f"}
UNSURE = {"unsure", "u", "maybe", "?", "idk"}


def norm_commerce(raw: str) -> str | None:
    v = (raw or "").strip().lower()
    if v in YES:
        return "yes"
    if v in NO:
        return "no"
    if v in UNSURE:
        return "unsure"
    return None


def norm_category(raw: str) -> str | None:
    v = (raw or "").strip().lower()
    return v or None


def labeler_name(path: pathlib.Path, row: dict) -> str:
    stated = (row.get("labeler") or "").strip()
    if stated:
        return stated.lower()
    stem = path.stem
    return stem.replace("label_sheet_", "").replace("labels_", "").lower() or stem.lower()


def majority(values: list[str]) -> tuple[str, bool]:
    """Most common value, and whether everyone agreed."""
    counts = collections.Counter(values)
    top, n = counts.most_common(1)[0]
    tied = [v for v, c in counts.items() if c == n]
    if len(tied) > 1:
        return "tie", False
    return top, len(counts) == 1


def fleiss_kappa(items: list[list[str]], categories: list[str]) -> float | None:
    """Fleiss' kappa. items = one list of ratings per item, all the same length."""
    items = [i for i in items if len(i) == len(items[0])] if items else []
    n = len(items[0]) if items else 0
    if not items or n < 2:
        return None
    N = len(items)
    k = len(categories)
    if k < 2:
        return None
    idx = {c: j for j, c in enumerate(categories)}

    p_j = [0.0] * k
    agree = []
    for ratings in items:
        counts = [0] * k
        for r in ratings:
            counts[idx[r]] += 1
        for j in range(k):
            p_j[j] += counts[j]
        agree.append((sum(c * c for c in counts) - n) / (n * (n - 1)))
    p_j = [v / (N * n) for v in p_j]
    p_bar = sum(agree) / N
    p_e = sum(v * v for v in p_j)
    if p_e >= 1:
        return None
    return (p_bar - p_e) / (1 - p_e)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="labels")
    args = ap.parse_args()
    ldir = pathlib.Path(args.labels)
    files = sorted(p for p in ldir.glob("*.csv")
                   if p.name not in {"merged.csv", "disagreements.csv", "keyword_scores.csv"})
    if not files:
        raise SystemExit(f"no label files in {ldir.resolve()} "
                         f"(expected labels/label_sheet_<name>.csv)")

    # chunk_id -> {"meta": {...}, "commerce": {labeler: value}, "category": {...}}
    rows: dict[str, dict] = {}
    labelers: set[str] = set()

    for path in files:
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                cid = (row.get("chunk_id") or "").strip()
                if not cid:
                    continue
                who = labeler_name(path, row)
                labelers.add(who)
                rec = rows.setdefault(cid, {"meta": {}, "commerce": {}, "category": {}})
                rec["meta"] = {
                    "slice": row.get("slice", ""),
                    "state": row.get("state", ""),
                    "header": (row.get("header") or "")[:120],
                    "function": row.get("function", ""),
                    "topic": row.get("topic", ""),
                    "matched": row.get("matched", ""),
                    "notes": " | ".join(
                        x for x in [rec["meta"].get("notes", ""), (row.get("notes") or "").strip()] if x
                    ),
                }
                c = norm_commerce(row.get("is_commerce", ""))
                if c:
                    rec["commerce"][who] = c
                g = norm_category(row.get("category", ""))
                if g:
                    rec["category"][who] = g

    people = sorted(labelers)
    ldir.mkdir(exist_ok=True)

    merged_path = ldir / "merged.csv"
    dis_path = ldir / "disagreements.csv"
    fields = (["chunk_id", "slice", "state", "function", "topic", "header", "matched"]
              + [f"commerce_{p}" for p in people]
              + [f"category_{p}" for p in people]
              + ["commerce_majority", "commerce_unanimous", "category_majority",
                 "category_unanimous", "n_labelers", "notes"])

    out_rows = []
    for cid, rec in rows.items():
        cvals = [rec["commerce"][p] for p in people if p in rec["commerce"]]
        gvals = [rec["category"][p] for p in people if p in rec["category"]]
        cmaj, cuni = majority(cvals) if cvals else ("", False)
        gmaj, guni = majority(gvals) if gvals else ("", False)
        out_rows.append({
            "chunk_id": cid, **{k: rec["meta"].get(k, "") for k in
                                ["slice", "state", "function", "topic", "header", "matched"]},
            **{f"commerce_{p}": rec["commerce"].get(p, "") for p in people},
            **{f"category_{p}": rec["category"].get(p, "") for p in people},
            "commerce_majority": cmaj, "commerce_unanimous": cuni,
            "category_majority": gmaj, "category_unanimous": guni,
            "n_labelers": len(cvals), "notes": rec["meta"].get("notes", ""),
        })

    with merged_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    contested = [r for r in out_rows
                 if r["n_labelers"] >= 2 and (not r["commerce_unanimous"] or not r["category_unanimous"])]
    contested.sort(key=lambda r: (r["commerce_unanimous"], r["category_unanimous"]))
    with dis_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(contested)

    # Kappa over rows everyone covered.
    full_c, full_g = [], []
    for rec in rows.values():
        if all(p in rec["commerce"] for p in people) and len(people) >= 2:
            full_c.append([rec["commerce"][p] for p in people])
        if all(p in rec["category"] for p in people) and len(people) >= 2:
            full_g.append([rec["category"][p] for p in people])
    k_c = fleiss_kappa(full_c, ["yes", "no", "unsure"])
    cats = sorted({v for item in full_g for v in item})
    k_g = fleiss_kappa(full_g, cats) if cats else None

    # Keyword scores, from the majority call on boundary rows.
    hits = collections.Counter()
    yes_hits = collections.Counter()
    for r in out_rows:
        if not r["matched"] or not r["commerce_majority"]:
            continue
        for kw in [x.strip() for x in r["matched"].split(";") if x.strip()]:
            hits[kw] += 1
            if r["commerce_majority"] == "yes":
                yes_hits[kw] += 1
    with (ldir / "keyword_scores.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["keyword", "rows_labeled", "called_commerce", "share_commerce"])
        for kw, n in hits.most_common():
            w.writerow([kw, n, yes_hits[kw], round(yes_hits[kw] / n, 3)])

    print(f"label files      {len(files)}  ({', '.join(people)})")
    print(f"rows seen        {len(rows):,}")
    print(f"rows all covered {len(full_c):,}")
    print(f"disagreements    {len(contested):,}  -> {dis_path}")
    print(f"Fleiss kappa     is_commerce {k_c if k_c is None else round(k_c, 3)}, "
          f"category {k_g if k_g is None else round(k_g, 3)}")
    print(f"wrote            {merged_path}, {dis_path}, {ldir / 'keyword_scores.csv'}")


if __name__ == "__main__":
    main()
