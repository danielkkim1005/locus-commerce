"""Cut the round-2 labeling sheet: three strata, shuffled, with the labels withheld.

Round 1 drew 150 from `business` and 150 from `boundary`, kept the slice and topic
columns in the sheet, and listed the two slices one after the other. That gave the
labeler the answer before they read the text: a row's slice told them LOCUS had
already called it Business, and the sheet's ordering told them where the slice
changed. Round 2 withholds all of it and shuffles.

Three strata, so the sheet can answer three different questions:

  business   topic == 'Business'          how we do on rows LOCUS already labels
  boundary   keyword hit in the header,   the contested rows the slice was built for
             topic != 'Business'
  random     any row at all               prevalence anchor, and the only stratum
                                          that can catch commerce both the LOCUS
                                          label and the keyword list miss

The random stratum is the point of this round. business + boundary is a biased
frame by construction; sampling it forever cannot tell us what fraction of
commerce it misses. 15 random rows is a thin estimate, but it is the first one.

Rows labeled in round 1 are excluded by default, so this is a fresh sample.

Two files come out:

  out/round2_sheet.csv   what labelers get: text, blank columns, nothing else
  out/round2_key.csv     slice / topic / function / jurisdiction, joined on row_id
                         Coordinator keeps this. Do not send it to labelers.

Usage, with no local copy of the corpus:

    pip install duckdb
    python export_round2.py --hf

Or against a local LOCUS-v1 sitting next to the repo:

    python export_round2.py

Options:

    --data         folder of train-*.parquet shards (default: ../LOCUS-v1/data),
                   or a remote glob DuckDB can read (hf://, s3://, https://)
    --hf           read LOCUS-v1 straight off Hugging Face. No download, no token.
    --out          output folder (default: out)
    --keywords     keyword file (default: commerce_keywords.txt)
    --n-business   rows from topic == 'Business' (default: 30)
    --n-boundary   rows from the keyword/boundary slice (default: 30)
    --n-random     rows sampled from all of LOCUS (default: 15)
    --seed         sampling and shuffle seed (default: 71; round 1 used 70)
    --chars        characters of text per row (default: 6000)
    --exclude      CSV with a chunk_id column, whose rows are held out
                   (default: labels/round1_clean.csv)

Nothing here writes to the LOCUS-v1 folder.
"""

import argparse
import csv
import pathlib
import random
import re
import sys
import textwrap

import duckdb

from export_commerce import (CHUNK_ID, HF_SOURCE, keyword_regex, load_keywords,
                             parquet_source, sql_labels, sql_list)

# What the labeler fills in. Must match the columns in definition_v2.md.
BLANK_COLUMNS = [
    "tier",             # core / adjacent / not   (blank if unresolvable)
    "adjacent_reason",  # required iff tier == adjacent
    "category",         # entry / operation / exit / other
    "unresolvable",     # blank / truncated / no-context
    "step",             # which decision-procedure step decided it, 1-5
    "notes",
    "labeler",
]

# Withheld from the sheet, kept in the key. `slice` and `topic` are the answer;
# `function` leaks it too, since topic is only ever set on Rules/Enforcement rows.
# Jurisdiction goes in the key because LABELING.md tells labelers not to look the
# jurisdiction up, and a state column is an invitation to.
KEY_COLUMNS = ["slice", "topic", "function", "matched", "state", "city", "county"]


def load_excluded(path: pathlib.Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if "chunk_id" not in (reader.fieldnames or []):
            raise SystemExit(f"{path} has no chunk_id column")
        return {row["chunk_id"] for row in reader if row["chunk_id"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../LOCUS-v1/data",
                    help="folder of train-*.parquet shards, or a remote glob "
                         "(hf://, s3://, https://). See --hf.")
    ap.add_argument("--hf", action="store_true",
                    help="read LOCUS-v1 off Hugging Face instead of a local copy; "
                         "no 1.8 GB download, no token (the dataset is public)")
    ap.add_argument("--out", default="out")
    ap.add_argument("--keywords", default="commerce_keywords.txt")
    ap.add_argument("--n-business", type=int, default=30)
    ap.add_argument("--n-boundary", type=int, default=30)
    ap.add_argument("--n-random", type=int, default=15)
    ap.add_argument("--seed", type=int, default=71)
    ap.add_argument("--chars", type=int, default=6000)
    ap.add_argument("--exclude", default="labels/round1_clean.csv")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    words = load_keywords(pathlib.Path(args.keywords))
    excluded = load_excluded(pathlib.Path(args.exclude))
    print(f"holding out {len(excluded)} chunk_ids from {args.exclude}")

    con = duckdb.connect()
    glob, source = parquet_source(con, HF_SOURCE if args.hf else args.data)
    print(f"reading {source}")
    con.execute(f"""
        CREATE OR REPLACE VIEW locus AS
        SELECT {CHUNK_ID} AS chunk_id, * FROM read_parquet('{glob}')
    """)

    # Oversample, then drop held-out rows in Python and trim to size. Simpler than
    # pushing a 97-element NOT IN list through the sampler, and the margin is wide
    # enough that a round-1 collision cannot starve a stratum.
    over = 4
    big = "(" + "|".join(keyword_regex(w) for w in words) + ")"
    matched = (f"list_transform(list_filter(list_zip({sql_list(words)}, {sql_labels(words)}),"
               f" z -> regexp_matches(lower(header), z[1])), z -> z[2])")

    strata = {
        # The filter has to sit in a CTE. With `WHERE topic = 'Business'` inline,
        # DuckDB pushes USING SAMPLE below the filter: it samples n rows from the
        # whole corpus and *then* keeps the Business ones, so asking for 120 of 256
        # Business rows returns about 13. Sampling a CTE, a view, or a table applies
        # the sample to the filtered relation, which is what we want.
        "business": f"""
            WITH cand AS (SELECT * FROM locus WHERE topic = 'Business')
            SELECT chunk_id, state, city, county, function, topic, header, content,
                   '' AS matched
            FROM cand
            USING SAMPLE {args.n_business * over} ROWS (reservoir, {args.seed})
        """,
        "boundary": f"""
            WITH cand AS (
                SELECT * FROM locus
                WHERE topic IS DISTINCT FROM 'Business'
                  AND regexp_matches(lower(header), '{big.replace("'", "''")}')
            )
            SELECT chunk_id, state, city, county, function, topic, header, content,
                   array_to_string({matched}, '; ') AS matched
            FROM cand
            USING SAMPLE {args.n_boundary * over} ROWS (reservoir, {args.seed})
        """,
        # No filter at all. This is the stratum that can surprise us.
        "random": f"""
            SELECT chunk_id, state, city, county, function, topic, header, content,
                   '' AS matched
            FROM locus
            USING SAMPLE {args.n_random * over} ROWS (reservoir, {args.seed})
        """,
    }
    wanted = {"business": args.n_business, "boundary": args.n_boundary,
              "random": args.n_random}

    rng = random.Random(args.seed)
    picked: list[dict] = []
    seen: set[str] = set(excluded)
    for name, sql in strata.items():
        # .df() gives VARCHAR columns pandas' `str` dtype, whose missing value is
        # truthy and formats as the literal "nan", so `x or ""` lets "nan" through
        # into the output. LOCUS leaves topic NULL on every Process and Context
        # row, so that is a third of the corpus, not an edge case.
        #
        # .where(frame.notna(), None) does NOT fix it: on the `str` dtype pandas
        # coerces the None straight back to its own NA. Going through object dtype
        # first is what makes the mask stick.
        frame = con.sql(sql).df()
        rows = frame.astype(object).mask(frame.isna(), None).to_dict("records")
        rng.shuffle(rows)
        kept = []
        for row in rows:
            if row["chunk_id"] in seen:
                continue
            seen.add(row["chunk_id"])
            row["slice"] = name
            kept.append(row)
            if len(kept) == wanted[name]:
                break
        if len(kept) < wanted[name]:
            print(f"warning: {name} yielded {len(kept)} of {wanted[name]} rows",
                  file=sys.stderr)
        picked.extend(kept)
        print(f"{name:9} {len(kept):3} rows")

    # One shuffle over everything, so slice is not recoverable from position.
    rng.shuffle(picked)

    sheet_path = out / "round2_sheet.csv"
    key_path = out / "round2_key.csv"
    sheet_cols = (["row_id", "chunk_id", "header", "text", "text_truncated"]
                  + BLANK_COLUMNS)
    truncated = 0

    with sheet_path.open("w", newline="", encoding="utf-8") as sf, \
         key_path.open("w", newline="", encoding="utf-8") as kf:
        sheet = csv.DictWriter(sf, fieldnames=sheet_cols)
        key = csv.DictWriter(kf, fieldnames=["row_id", "chunk_id"] + KEY_COLUMNS
                             + ["full_chars"])
        sheet.writeheader()
        key.writeheader()
        for i, row in enumerate(picked, start=1):
            content = row["content"] or ""
            cut = len(content) > args.chars
            truncated += cut
            # Round 1 cut text at 2000 chars and six labels came back saying "cut
            # off" or "list is missing". Some of that was our export, not LOCUS
            # chunking, and the two mean different things: ours is a bug, LOCUS's is
            # a finding. Say which, so `unresolvable: truncated` stays meaningful.
            sheet.writerow({
                "row_id": i,
                "chunk_id": row["chunk_id"],
                "header": row["header"] or "",
                "text": content[:args.chars],
                "text_truncated": "yes" if cut else "no",
                **{c: "" for c in BLANK_COLUMNS},
            })
            key.writerow({
                "row_id": i,
                "chunk_id": row["chunk_id"],
                "slice": row["slice"],
                "topic": row["topic"] or "",
                "function": row["function"] or "",
                "matched": row["matched"] or "",
                "state": row["state"] or "",
                "city": row["city"] or "",
                "county": row["county"] or "",
                "full_chars": len(content),
            })

    counts = {name: sum(1 for r in picked if r["slice"] == name) for name in strata}
    summary = textwrap.dedent(f"""\
        round 2 sheet    {len(picked)} rows, shuffled, seed {args.seed}
        strata           business {counts['business']}  boundary {counts['boundary']}  random {counts['random']}
        held out         {len(excluded)} round-1 chunk_ids
        text per row     {args.chars} chars ({truncated} rows hit the limit)
        withheld         {', '.join(KEY_COLUMNS)}
        to fill in       {', '.join(BLANK_COLUMNS)}

        sheet            {sheet_path.resolve()}
        key              {key_path.resolve()}   <- coordinator only, do not share
        """)
    (out / "round2_summary.txt").write_text(summary, encoding="utf-8")
    print()
    print(summary)
    con.close()


if __name__ == "__main__":
    main()
