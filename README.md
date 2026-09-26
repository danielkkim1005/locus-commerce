# locus-commerce

Tooling for WP3 (Commerce) of the Local Laws Observatory URAP. It cuts the
LOCUS-v1 corpus into the slices we need to answer Denis's question: what is and
isn't commerce?

## Setup

You need a local copy of LOCUS-v1 (about 1.8 GB). It is not in this repo.

```bash
git clone <this repo>
cd locus-commerce
pip install duckdb

# LOCUS-v1 should sit next to this folder:
#   somewhere/
#     locus-commerce/     <- this repo
#     LOCUS-v1/data/train-00000-of-00008.parquet ...
python export_commerce.py
```

If LOCUS-v1 is elsewhere, pass `--data /path/to/LOCUS-v1/data`.

Get LOCUS-v1 from https://huggingface.co/datasets/LocalLaws/LOCUS-v1 (needs
git-lfs), or ask and I'll share the folder.

## What it produces

Everything lands in `out/`, which is gitignored.

| File | What it is |
| --- | --- |
| `summary.txt` | row counts for the run, and where the boundary rows sit in the LOCUS taxonomy |
| `business.parquet` | rows where `topic == 'Business'` |
| `boundary.parquet` | rows where `topic != 'Business'` but the header hit a keyword, plus which keywords hit |
| `label_sheet.csv` | a sample of both slices with blank columns to fill in |
| `keyword_hits.csv` | header hits per keyword |
| `locus.duckdb` | the views, if you'd rather query than read files |

To query directly:

```bash
python -c "import duckdb; duckdb.connect('out/locus.duckdb').sql('select * from boundary limit 5').show()"
```

## The two slices

`business` is the plain `topic == 'Business'` selection. On one shard it was
about 11% of rows.

`boundary` is the part worth arguing about: rows LOCUS did *not* label Business
whose section header contains a commerce word. About another 9%.

The reason for the second slice: LOCUS only assigns a topic when a chunk is
classified Rules or Enforcement. Chunks classified Process or Context get
`topic = NULL`, and much of the licensing machinery lives there, such as how to
apply, what the clerk does, hearings, renewals. Those rows cannot appear under
`topic == 'Business'` no matter how the label was assigned. In a one-shard run,
about 4,300 boundary rows were Process or Context.

## How we use the keyword list

`commerce_keywords.txt` is a way to find candidates for a person to read. It is
not the definition of commerce.

That distinction is what keeps a loose keyword cheap. Nothing enters the final
set without someone reading it, so a bad keyword costs reading time rather than
bending our numbers. A word none of us thought of is worse, because the rows it
would have caught are invisible to us.

Prune with evidence, not taste. Once a sample is labeled, each keyword can be
scored by the share of its hits that turned out to be commerce, and the weak ones
dropped with a number attached. `keyword_hits.csv` is the starting point;
`sign` and `permit` are the obvious suspects for low precision.

Edit the file, rerun, and say in the commit message what you changed and why.

## Labeling

`out/label_sheet.csv` opens in Excel or Google Sheets. No code needed. Fill in:

- `is_commerce` — yes / no / unsure
- `category` — entry / operation / exit / other (from the WP3 stub)
- `notes` — why, if the call was hard. These become the edge-case log.
- `labeler` — your name

Leave the other columns alone. `chunk_id` is a hash of the row's own text, so
it's the same id on everyone's machine and our labels can be joined on it.

Two of us labeling the *same* sheet independently is the point. `--sample` and
`--seed` are fixed so we all get identical rows; don't change them without
telling the group. Save your copy as `labels/label_sheet_<yourname>.csv`.

## Definition

See `definition.md`. That file, not this one, is the deliverable.
