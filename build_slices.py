"""Build the WP3 (Commerce) working slices from LOCUS-v1.

Renamed from export_commerce.py: this builds the corpus slices, while
cut_sheet.py samples a labeling sheet out of them. The old names made them look
like a pair of round variants, which they are not.

Two slices come out of this:

  business   rows where topic == 'Business' (the label LOCUS already assigns)
  boundary   rows where topic != 'Business' but the section HEADER matches a
             keyword from commerce_keywords.txt

The boundary slice exists because LOCUS only assigns a topic to chunks it
classified as Rules or Enforcement. Chunks classified Process or Context get
topic = NULL, and a lot of licensing procedure (applications, hearings,
renewals) lives there. Those rows can never appear under topic == 'Business'.

The keyword list finds candidates for a person to read. It is not the definition
of commerce.

Usage, from inside the repo folder, with LOCUS-v1 sitting next to it:

    pip install duckdb pandas
    python build_slices.py
    python build_slices.py --hf      # read the shards off Hugging Face instead

Options:

    --data      folder holding the train-*.parquet shards, or a remote glob
                (default: ../LOCUS-v1/data)
    --hf        read LOCUS-v1 off Hugging Face; no download, no token
    --out       output folder (default: out)
    --keywords  keyword file (default: commerce_keywords.txt)
    --sample    rows per slice in the labeling sheet (default: 150)
    --seed      sampling seed, so everyone gets the same sheet (default: 70)

Outputs, in --out:

    locus.duckdb       persistent DB with views: locus, business, boundary
    business.parquet   the business slice
    boundary.parquet   the boundary slice, with the keywords that matched
    label_sheet.csv    sample of both slices with empty columns to fill in
    keyword_hits.csv   how many header matches each keyword produced
    summary.txt        row counts, written so runs can be compared

Nothing here writes to the LOCUS-v1 folder.
"""

import argparse
import pathlib
import re
import textwrap

import duckdb

from wp3.corpus import (CHUNK_ID, HF_SOURCE, keyword_regex, load_keywords,
                        parquet_source, sql_labels, sql_list)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../LOCUS-v1/data")
    ap.add_argument("--hf", action="store_true",
                    help="read LOCUS-v1 off Hugging Face instead of a local copy")
    ap.add_argument("--out", default="out")
    ap.add_argument("--keywords", default="commerce_keywords.txt")
    ap.add_argument("--sample", type=int, default=150)
    ap.add_argument("--seed", type=int, default=70)
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    words = load_keywords(pathlib.Path(args.keywords))

    con = duckdb.connect((out / "locus.duckdb").as_posix())
    glob, source = parquet_source(con, HF_SOURCE if args.hf else args.data)
    print(f"reading {source}")
    con.execute(f"""
        CREATE OR REPLACE VIEW locus AS
        SELECT {CHUNK_ID} AS chunk_id, * FROM read_parquet('{glob}')
    """)
    con.execute("""
        CREATE OR REPLACE VIEW business AS
        SELECT * FROM locus WHERE topic = 'Business'
    """)
    # Two stages, because running ~100 regexes over 2.2M rows is slow: one combined
    # pattern narrows to candidate rows, then per-keyword matching runs only on those.
    big = "(" + "|".join(keyword_regex(w) for w in words) + ")"
    matched = (f"list_transform(list_filter(list_zip({sql_list(words)}, {sql_labels(words)}),"
               f" z -> regexp_matches(lower(header), z[1])), z -> z[2])")
    # A previous run may have left `boundary` as either a view or a table in the
    # persistent DB, and DuckDB refuses to drop one as the other.
    for stmt in ("DROP TABLE IF EXISTS boundary", "DROP VIEW IF EXISTS boundary"):
        try:
            con.execute(stmt)
        except duckdb.CatalogException:
            pass
    con.execute(f"""
        CREATE OR REPLACE TABLE boundary AS
        WITH cand AS (
            SELECT * FROM locus
            WHERE topic IS DISTINCT FROM 'Business'
              AND regexp_matches(lower(header), '{big.replace("'", "''")}')
        )
        SELECT *, {matched} AS matched_keywords FROM cand
    """)

    total = con.sql("SELECT count(*) FROM locus").fetchone()[0]
    n_bus = con.sql("SELECT count(*) FROM business").fetchone()[0]
    n_bnd = con.sql("SELECT count(*) FROM boundary").fetchone()[0]

    con.execute(f"COPY business TO '{(out / 'business.parquet').as_posix()}' (FORMAT PARQUET)")
    con.execute(f"COPY boundary TO '{(out / 'boundary.parquet').as_posix()}' (FORMAT PARQUET)")

    # One hit per (row, keyword), so a keyword can be scored on its own later.
    con.execute(f"""
        COPY (
            SELECT w AS keyword, count(*) AS header_hits
            FROM (SELECT unnest(matched_keywords) AS w FROM boundary)
            GROUP BY w ORDER BY header_hits DESC
        ) TO '{(out / 'keyword_hits.csv').as_posix()}' (FORMAT CSV, HEADER)
    """)

    # Labeling sheet: readable in Excel or Sheets, no code needed to fill in.
    # is_commerce / category / notes / labeler are left blank on purpose.
    con.execute(f"""
        COPY (
            WITH picked AS (
                SELECT chunk_id, 'business' AS slice, state, city, county, function,
                       topic, header, content, '' AS matched
                FROM business USING SAMPLE {args.sample} ROWS (reservoir, {args.seed})
                UNION ALL
                SELECT chunk_id, 'boundary' AS slice, state, city, county, function,
                       topic, header, content, array_to_string(matched_keywords, '; ')
                FROM boundary USING SAMPLE {args.sample} ROWS (reservoir, {args.seed})
            )
            SELECT chunk_id, slice, state, city, county, function, topic, header,
                   substr(content, 1, 2000) AS content_first_2000, matched,
                   '' AS is_commerce, '' AS category, '' AS notes, '' AS labeler
            FROM picked
        ) TO '{(out / 'label_sheet.csv').as_posix()}' (FORMAT CSV, HEADER)
    """)

    breakdown = con.sql("""
        SELECT function, coalesce(topic, '(no topic)') AS topic, count(*) AS rows
        FROM boundary GROUP BY 1, 2 ORDER BY rows DESC
    """).df()

    summary = textwrap.dedent(f"""\
        source           {source}
        keywords         {len(words)}   (from {args.keywords})
        rows total       {total:,}
        topic=Business   {n_bus:,}  ({100 * n_bus / total:.1f}%)
        boundary set     {n_bnd:,}  ({100 * n_bnd / total:.1f}%)

        Where the boundary rows sit in the LOCUS taxonomy:

        {breakdown.to_string(index=False)}
        """)
    (out / "summary.txt").write_text(summary, encoding="utf-8")
    print(summary)
    print(f"wrote {out.resolve()}")
    con.close()


if __name__ == "__main__":
    main()
