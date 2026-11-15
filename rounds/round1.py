"""Round 1's merge, as it was run, with the shared code lifted into wp3/.

Round 1 asked a single yes/no/unsure question (`is_commerce`) plus a free-text
`category`, so its scoring cannot be folded into round 2's. It is kept because
its outputs are published numbers and must stay reproducible, not because
anything new should use this schema.

    python merge_round.py --round 1
"""

import collections
import csv
import pathlib

from wp3 import agreement
from wp3.sheets import labeler_name, sheet_files, norm_legacy_category, norm_legacy_commerce

def merge(ldir: pathlib.Path, outdir: pathlib.Path) -> None:
    files = sheet_files(ldir, 1)
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
                who = labeler_name(path)
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
                c = norm_legacy_commerce(row.get("is_commerce", ""))
                if c:
                    rec["commerce"][who] = c
                g = norm_legacy_category(row.get("category", ""))
                if g:
                    rec["category"][who] = g

    people = sorted(labelers)
    outdir.mkdir(parents=True, exist_ok=True)

    merged_path = outdir / "merged.csv"
    dis_path = outdir / "disagreements.csv"
    fields = (["chunk_id", "slice", "state", "function", "topic", "header", "matched"]
              + [f"commerce_{p}" for p in people]
              + [f"category_{p}" for p in people]
              + ["commerce_majority", "commerce_unanimous", "category_majority",
                 "category_unanimous", "n_labelers", "notes"])

    out_rows = []
    for cid, rec in rows.items():
        cvals = [rec["commerce"][p] for p in people if p in rec["commerce"]]
        gvals = [rec["category"][p] for p in people if p in rec["category"]]
        cmaj, cuni = agreement.majority(cvals) if cvals else ("", False)
        gmaj, guni = agreement.majority(gvals) if gvals else ("", False)
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
    k_c = agreement.fleiss_kappa(full_c, ["yes", "no", "unsure"])
    cats = sorted({v for item in full_g for v in item})
    k_g = agreement.fleiss_kappa(full_g, cats) if cats else None
    # Kappa over rows where every labeler named exactly ONE category, so the
    # statistic is not dominated by multi-label cells.
    single = [i for i in full_g if all("," not in v for v in i)]
    cats1 = sorted({v for item in single for v in item})
    k_g1 = agreement.fleiss_kappa(single, cats1) if cats1 else None

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
    with (outdir / "keyword_scores.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["keyword", "rows_labeled", "called_commerce", "share_commerce"])
        for kw, n in hits.most_common():
            w.writerow([kw, n, yes_hits[kw], round(yes_hits[kw] / n, 3)])

    print(f"label files      {len(files)}  ({', '.join(people)})")
    print(f"rows seen        {len(rows):,}")
    print(f"rows all covered {len(full_c):,}")
    print(f"disagreements    {len(contested):,}  -> {dis_path}")
    print(f"Fleiss kappa     is_commerce {k_c if k_c is None else round(k_c, 3)} "
          f"(n={len(full_c)})")
    print(f"                 category    {k_g if k_g is None else round(k_g, 3)} "
          f"(n={len(full_g)}, multi-label cells included)")
    print(f"                 category    {k_g1 if k_g1 is None else round(k_g1, 3)} "
          f"(n={len(single)}, single-category rows only)")
    per = {}
    for rec in rows.values():
        for who, v in rec["commerce"].items():
            per.setdefault(who, collections.Counter())[v] += 1
    print("\nyes / no / unsure by labeler (a large spread here is itself the finding):")
    for who in people:
        c = per.get(who, collections.Counter())
        tot = sum(c.values()) or 1
        print(f"  {who:<10} yes {c['yes']:>3} ({100*c['yes']/tot:.0f}%)  "
              f"no {c['no']:>3}  unsure {c['unsure']:>3}  total {tot}")
    print(f"wrote            {merged_path}, {dis_path}, {outdir / 'keyword_scores.csv'}")

