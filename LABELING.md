# Labeling rounds: how a round actually runs

One round, start to finish, under codebook v3. This replaces the round-1
version of this file, which described the `is_commerce` yes/no/unsure schema
that no longer exists.

The codebook itself is `codebook/v3.md`. Read that before labeling; this file
is only the logistics.

## Why separate copies

Independence is the whole point. If everyone types into one shared sheet we can
see each other's calls, and the agreement number stops measuring anything. Three
people, three files, no shared tab, and no discussion of specific rows until all
three are in.

General questions about the *procedure* go to the shared clarifications log, so
the answer reaches everyone at once. Questions about a *row* wait.

## Roles

- **Coordinator** (Daniel): cuts the sheet, makes the copies, collects them,
  runs the merge, commits the round.
- **Labelers** (all of us, coordinator included): one sheet each.

## 1. Coordinator: cut the sheet

```bash
cd ~/Desktop/LOCUS/locus-commerce
python cut_sheet.py --round 3
```

Writes two files:

- `out/round3_sheet.csv` — the rows: `row_id`, `chunk_id`, `header`, `text`,
  `text_truncated`, and the blank columns to fill in.
- `out/round3_key.csv` — **coordinator only.** The stratum, topic, function and
  jurisdiction for each row. This is what the sheet withholds, and it is what
  the merge joins back for the per-stratum and per-keyword breakdowns.

The sheet withholds provenance on purpose. Round 1 showed `slice` and `topic` in
the sheet and listed the slices one after the other, which handed the labeler
LOCUS's answer before they read the text.

`--seed` is fixed so everyone gets identical rows. Do not change it mid-round;
if you do, say so, because it makes the round incomparable with the last one.

Rows already labeled in earlier rounds are held out, via `--exclude`.

## 2. Coordinator: one copy per labeler

```bash
python make_sheets.py
```

One `.xlsx` per person, every coded column a dropdown, `labeler` prefilled.
Upload to Drive, let it convert, share each copy with that person only, as
editor. Keep the master untouched.

CSV cannot carry data validation, which is why these are `.xlsx`. Google Sheets
preserves the dropdowns on import.

## 3. Labelers: fill in the sheet

Run the four-step procedure in `codebook/v3.md`. Stop at the first step that
answers. Columns:

| Column | Values |
| --- | --- |
| `tier` | core / adjacent / not — blank when `unresolvable` is set |
| `adjacent_reason` | required **iff** `tier = adjacent`; one of eight codes |
| `category` | entry / operation / exit / other, on core and adjacent rows |
| `unresolvable` | blank, or `no-context` |
| `step` | 1–4, the step that decided the row |
| `confidence` | High / Medium / Low |
| `notes` | required on every row |

Leave `row_id`, `chunk_id`, `header`, `text` and `text_truncated` alone.
`chunk_id` is what the merge joins on, and an edited id silently drops the row.

`text_truncated` is pre-filled and is not yours to set: it records whether *our
export* cut the text, which is a property of the pipeline, not a judgment.

**Judge the text in front of you.** Do not look up the jurisdiction, the parent
chapter, or the rest of the code. If the text alone cannot answer it, that is a
finding, and step 1 says what to do with it.

**Notes are required.** On a High-confidence row write exactly "High confidence,
no notes needed." On anything else, a sentence or two: which tiers or codes you
were choosing between, whether the row mixes several functions, whether the text
is incomplete, whether the formatting is odd. These become the edge-case log,
which is what edits the codebook.

**Calibration first.** Label rows 1–10, then stop and compare tier distributions
with the group before doing the rest. Round 1's yes-rates ranged 47% to 85% on
identical rows; that is what this catches. Do not skip it.

## 4. Labelers: hand it back

File, Download, Microsoft Excel. Send the coordinator the file, keeping the
name. Do not reconcile with anyone first — the merge wants your independent
read.

## 5. Coordinator: merge

Put every file in `labels/`, then:

```bash
python merge_round.py --round 3
```

Writes `results/round3/`:

- `round3_merged.csv` — one row per chunk, each person's call side by side
- `round3_disagreements.csv` — the rows to talk through, most contested first
- `round3_keyword_scores.csv` — per keyword, the share called core
- `round3_summary.txt` — the printed report, so a round is committable as a number

It reports Fleiss' κ and Gwet's AC1 together. Kappa is the comparison, because
it is what round 1 and LOCUS-Fines reported. AC1 is there because kappa
collapses when one category dominates, which in a stratified sheet is a property
of the sample rather than of the labelers — round 1's business slice gave κ 0.06
at 53% identical answers. A large κ/AC1 gap is itself the finding.

**A low kappa means the codebook is unclear, not that someone was careless.**

## 6. Everyone: work the disagreements

```bash
python pick_disagreements.py
```

Walk the queue together. Every resolved case becomes either a line in the
codebook or an entry in the edge-case log. That editing is the deliverable; the
labels are how we find out what needs editing.

Two rules that came out of round 2 and are worth keeping in view:

- Rows where one person set `unresolvable` and another assigned a tier are a
  *legibility* dispute, not a dispute about commerce. 22 of 75 round-2 rows were
  this. Decide the asymmetric-`unresolvable` rule before quoting a number.
- `adjacent` is a closed list. A row that feels adjacent with no fitting reason
  code is a finding for the log, not a free-text reason.

## 7. Coordinator: commit the round

```bash
git add labels/ results/ codebook/ commerce_keywords.txt
git commit -m "round 3: 3 labelers, N rows, kappa 0.xx; dropped 'permit*' (0/16)"
```

The commit message is where the round's numbers live. Write them in.

## Notes

Rounds get smaller. The first finds where the definition is vague; later ones
sample the parts that stayed vague.

If someone relabels rows after the discussion, they resend the whole file and
the coordinator replaces it. Never hand-edit a file in `labels/`.

**No AI assistance in a human round.** A model may be run against the codebook
as a separately declared annotator, in its own column with its own agreement
statistics — that is what `llm_ablation.py` does. What is not allowed is a
model's output entering a human's column, because the exercise measures whether
a specification written for people is reproducible, and a mixed column measures
deference instead.
