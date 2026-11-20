# locus-commerce

Tooling and annotation data for **WP3 (Commerce)** of the Local Laws Observatory
URAP. The question the group was given: what does and does not count as commerce
in the LOCUS-v1 corpus of US municipal and county ordinances?

The deliverable is the codebook, not the code. Everything here exists to cut
samples for people to label, and to measure how much they agreed.

## Layout

```
codebook/            the definition, by version. v3.md is current.
wp3/                 shared library: schema, agreement statistics, sheet reading
rounds/              one module per labeling round's scoring
labels/              the sheets people filled in — inputs, never regenerated
results/             everything the scripts derive from them
prompts/             the fragments llm_ablation.py composes
out/                 corpus slices and cut sheets (gitignored, large)
```

The split between `labels/` and `results/` is the one worth respecting. A sheet
in `labels/` is someone's afternoon and cannot be reproduced; everything in
`results/` can be regenerated from those sheets plus a script, and is tracked
only so a commit's reported numbers stay readable without a rerun.

## Scripts

| Script | What it does |
| --- | --- |
| `build_slices.py` | builds the `business` and `boundary` slices from the LOCUS-v1 shards |
| `cut_sheet.py --round N` | samples a stratified labeling sheet (business, boundary, random) straight from the corpus, with provenance withheld |
| `make_sheets.py` | turns a sheet CSV into one `.xlsx` per labeler, with dropdowns |
| `merge_round.py --round N` | merges the returned sheets, reports agreement, writes `results/roundN/` |
| `pick_disagreements.py` | ranks contested rows by how far apart the group actually was |
| `clean_round1.py` | builds round 1's intersection reference table |
| `llm_ablation.py` | runs a model against the frozen codebook in five prompt variants |

`build_slices.py` and `cut_sheet.py` used to be called `export_commerce.py` and
`export_round2.py`, which made them look like round variants of one operation.
They are two different operations: one reads the corpus, the other samples from
what it produced.

## Setup

```bash
git clone <this repo>
cd locus-commerce
pip install duckdb pandas openpyxl

python build_slices.py            # expects LOCUS-v1 beside this folder
python build_slices.py --hf       # or read the shards off Hugging Face directly
```

LOCUS-v1 is about 1.8 GB and is not in this repo. It lives on Hugging Face at
[LocalLaws/LOCUS-v1](https://huggingface.co/datasets/LocalLaws/LOCUS-v1). Clone
it next to this repo, or pass `--data /path/to/LOCUS-v1/data`. DuckDB can also stream the shards from the
Hub over range requests, which is what `--hf` does; the dataset is public, so no
token is needed.

## Running a round

See `LABELING.md` for the full procedure. In short:

```bash
python cut_sheet.py --round 3                 # writes out/round3_sheet.csv and the key
python make_sheets.py                          # one .xlsx per labeler
# ... people label, and send their files back into labels/ ...
python merge_round.py --round 3                # writes results/round3/
```

### The expert batch (round 3)

There is no further labeling round inside the group. The next labeled rows come
from the expert annotators, sampled with the defaults, which are set for that
batch:

```bash
python cut_sheet.py --round 3 \
    --n-business 30 --n-boundary 20 --n-pc 20 --n-random 30 --seed 72
```

That is 100 rows in four strata: `business` (topic is Business), `boundary`
(keyword hit, Rules or Enforcement), `process_ctx` (keyword hit, Process or
Context, the rows LOCUS can never call Business) and `random` (the whole
corpus, the only stratum that can show what the other three miss). Rows from
rounds 1 and 2 are held out. The flags repeat the defaults so the command stays
the record even if the defaults change.

`out/round<N>_key.csv` carries the stratum, topic, function and jurisdiction
columns that the labeling sheet deliberately withholds. It is coordinator-only
and gitignored. Without it `merge_round.py` still runs, but skips the stratum
and keyword sections.

## The two slices, and why there are two

`business` is the plain `topic == 'Business'` selection: 232,224 rows, 10.5% of
the corpus.

`boundary` is the part worth arguing about: rows LOCUS did *not* label Business
whose section header matches a commerce keyword. 106,379 rows, 4.8%, after
`permit*` was pruned. Rounds 1 and 2 were sampled from the earlier 168,013-row
(7.6%) frame that still included it.

The second slice exists because LOCUS assigns a `topic` only to chunks it
classified as Rules or Enforcement. Chunks classified Process or Context get
`topic = NULL`, and much of the licensing machinery lives there — how to apply,
what the clerk does, hearings, renewals. 17,262 boundary rows are Process or
Context (21,675 before the `permit*` prune), and no amount of classifier
accuracy would bring them under the Business label.

## The keyword list

`commerce_keywords.txt` finds candidates for a person to read. It is **not** the
definition of commerce.

That distinction is what keeps a loose keyword cheap: nothing enters the final
set without someone reading it, so a bad keyword costs reading time rather than
bending the numbers. A word nobody thought of is the worse failure, because the
rows it would have caught are invisible.

Prune with evidence. Once a round is labeled, `results/round<N>/` scores each
keyword by the share of its hits the group called core, and the weak ones go
with a number attached. `permit*` was retired on that evidence: 0 of 16 boundary
rows core in round 2, after 4 of 17 called commerce in round 1. It was also the
largest single source of boundary rows, so pruning it shrank the slice by 37%.
Say in the commit message what changed and why.

Matching is on word boundaries, and the convention is in the file: a bare word
matches the whole word, a trailing `*` matches a prefix. `licens*` catches
license, licensing and licensee; `tow` does not match "town". Plain substring
matching previously had `sign` matching "design" and accounted for 11% of
sampled boundary rows.

## Where the numbers are

- `results/round1/` — round 1: Fleiss' κ 0.232 on `is_commerce`, n=97
- `results/round2/` — round 2: κ 0.549 all rows, 0.724 core-vs-rest on legible
  rows, n=75 / 52
- `ROUND2_RESULTS.md` — the round-2 writeup, with the agreement ladder and the
  step-collapse analysis

Both rounds can be regenerated: `python merge_round.py --round 1` and
`--round 2` reproduce the committed CSVs byte for byte.
