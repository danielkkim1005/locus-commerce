"""Build the WP3 (Commerce) working slices from a local copy of LOCUS-v1.

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

    pip install duckdb
    python export_commerce.py

Options:

    --data      folder holding the train-*.parquet shards
                (default: ../LOCUS-v1/data)
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
import textwrap

import duckdb

# LOCUS-v1 has no row identifier, so we make a stable one from the row's own
# content. Same row, same id, on anyone's machine. Labels can be joined back on it.
CHUNK_ID = """md5(concat_ws('|', state, coalesce(city, ''), coalesce(county, ''),
                            coalesce(header, ''), coalesce(content, '')))"""


def load_keywords(path: pathlib.Path) -> list[str]:
    words = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            words.append(line.lower())
    if not words:
        raise SystemExit(f"no keywords found in {path}")
    return words


def sql_list(words: list[str]) -> str:
    """A DuckDB list literal. Single quotes are doubled; nothing else is allowed in."""
    inner = ", ".join("'" + w.replace("'", "''") + "'" for w in words)
    return "[" + inner + "]"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../LOCUS-v1/data")
    ap.add_argument("--out", default="out")
    ap.add_argument("--keywords", default="commerce_keywords.txt")
    ap.add_argument("--sample", type=int, default=150)
    ap.add_argument("--seed", type=int, default=70)
    args = ap.parse_args()

    data = pathlib.Path(args.data)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    words = load_keywords(pathlib.Path(args.keywords))

    glob = (data / "train-*.parquet").as_posix()
    shards = sorted(data.glob("train-*.parquet"))
    if not shards:
        raise SystemExit(f"no parquet shards under {data.resolve()} "
                         f"(pass --data if LOCUS-v1 is somewhere else)")

    con = duckdb.connect((out / "locus.duckdb").as_posix())
    con.execute(f"""
        CREATE OR REPLACE VIEW locus AS
        SELECT {CHUNK_ID} AS chunk_id, * FROM read_parquet('{glob}')
    """)
    con.execute("""
        CREATE OR REPLACE VIEW business AS
        SELECT * FROM locus WHERE topic = 'Business'
    """)
    con.execute(f"""
        CREATE OR REPLACE VIEW boundary AS
        SELECT *, list_filter({sql_list(words)}, w -> contains(lower(header), w))
                    AS matched_keywords
        FROM locus
        WHERE topic IS DISTINCT FROM 'Business'
          AND len(list_filter({sql_list(words)}, w -> contains(lower(header), w))) > 0
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
        shards read      {len(shards)}
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
