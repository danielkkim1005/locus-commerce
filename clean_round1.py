"""Build the round-1 reference table: only rows every labeler actually labeled.

Reads labels/label_sheet_<name>.csv, keeps the intersection of rows with a filled
is_commerce cell, normalizes the free-text cells, and writes one wide row per chunk
with each labeler's call beside the text.

    python clean_round1.py --labels labels --out round1_clean.csv
"""
import argparse, collections, csv, pathlib

YES = {"yes", "y", "true", "1", "t"}
NO = {"no", "n", "false", "0", "f"}
UNSURE = {"unsure", "u", "maybe", "?", "idk"}
CATS = ("entry", "operation", "exit", "other")
NOT_A_CATEGORY = {"", "n/a", "na", "none", "unsure", "?", "idk", "tbd"}


def norm_commerce(v):
    v = (v or "").strip().lower()
    return "yes" if v in YES else "no" if v in NO else "unsure" if v in UNSURE else ""


def norm_category(v):
    v = (v or "").strip().lower()
    if v in NOT_A_CATEGORY:
        return ""
    found = [c for c in CATS if c in v]
    return ",".join(sorted(found))


def name_of(path):
    stem = path.stem.replace("label_sheet_", "").replace("labels_", "").strip()
    return stem.split(" - ")[0].split("-")[0].strip().lower() or path.stem.lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="labels")
    ap.add_argument("--out", default="round1_clean.csv")
    args = ap.parse_args()
    files = sorted(p for p in pathlib.Path(args.labels).glob("*.csv")
                   if p.stem not in {"merged", "disagreements", "keyword_scores", "round1_clean"})

    per, meta = {}, {}
    for p in files:
        who = name_of(p)
        with p.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                cid = (row.get("chunk_id") or "").strip()
                if not cid:
                    continue
                meta.setdefault(cid, row)
                c = norm_commerce(row.get("is_commerce"))
                if c:
                    per.setdefault(cid, {})[who] = {
                        "commerce": c,
                        "category": norm_category(row.get("category")),
                        "notes": (row.get("notes") or "").strip(),
                    }

    people = sorted({w for v in per.values() for w in v})
    kept = [cid for cid, v in per.items() if len(v) == len(people)]
    kept.sort(key=lambda c: (meta[c]["slice"], meta[c]["state"], meta[c]["header"]))

    cols = (["chunk_id", "slice", "state", "city", "county", "function", "topic",
             "matched", "header", "content_first_2000"]
            + [f"{p}_commerce" for p in people]
            + [f"{p}_category" for p in people]
            + ["commerce_majority", "commerce_unanimous", "n_yes", "n_no", "n_unsure",
               "category_agreement"]
            + [f"{p}_notes" for p in people])

    out = []
    for cid in kept:
        m, v = meta[cid], per[cid]
        cvals = [v[p]["commerce"] for p in people]
        gvals = [v[p]["category"] for p in people]
        counts = collections.Counter(cvals)
        top, n = counts.most_common(1)[0]
        tied = [x for x, k in counts.items() if k == n]
        gset = {g for g in gvals if g}
        out.append({
            "chunk_id": cid,
            **{k: m.get(k, "") for k in ["slice", "state", "city", "county", "function",
                                         "topic", "matched", "header", "content_first_2000"]},
            **{f"{p}_commerce": v[p]["commerce"] for p in people},
            **{f"{p}_category": v[p]["category"] for p in people},
            "commerce_majority": "tie" if len(tied) > 1 else top,
            "commerce_unanimous": len(counts) == 1,
            "n_yes": counts["yes"], "n_no": counts["no"], "n_unsure": counts["unsure"],
            "category_agreement": ("none given" if not gset else
                                   "unanimous" if len(gset) == 1 and all(gvals) else "split"),
            **{f"{p}_notes": v[p]["notes"] for p in people},
        })

    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)

    dropped = len(per) - len(kept)
    print(f"labelers        {', '.join(people)}")
    print(f"rows kept       {len(kept)}  (labeled by all {len(people)})")
    print(f"rows dropped    {dropped}  (labeled by only some)")
    print(f"  by slice      {dict(collections.Counter(r['slice'] for r in out))}")
    print(f"  unanimous     {sum(1 for r in out if r['commerce_unanimous'])}")
    print(f"wrote           {pathlib.Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
