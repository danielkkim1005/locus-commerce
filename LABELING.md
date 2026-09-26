# Labeling rounds: how a round actually runs

One labeling round, start to finish. Daniel runs the export and the merge;
labelers only ever touch a spreadsheet in the browser.

The point of the separate copies is independence. If we all type into one shared
sheet we can see each other's calls, and the agreement number stops measuring
anything.

## Roles

- **Coordinator** (Daniel for now): runs `export_commerce.py`, makes the copies, collects them, runs `merge_labels.py`, commits the results.
- **Labelers** (all of us, including the coordinator): fill in one sheet each.

## The round

### 1. Coordinator: cut the sheet

```bash
cd ~/Desktop/LOCUS/locus-commerce
python export_commerce.py
```

`out/label_sheet.csv` is the sheet for this round. `--sample` and `--seed` are
fixed so everyone gets the same rows. Don't change either mid-round; if you do,
say so, because it makes this round incomparable to the last one.

### 2. Coordinator: one copy per labeler

Upload `out/label_sheet.csv` to Drive, let it convert to a Google Sheet, then
make one copy per person named `label_sheet_<name>`. Share each copy with that
person only, as editor. Keep the master untouched as a reference.

Three copies, three links, no shared tab.

### 3. Labelers: fill in four columns

Only these:

- `is_commerce` — yes / no / unsure
- `category` — entry / operation / exit / other
- `notes` — why, whenever the call was hard. These become the edge-case log, so they're the most valuable column in the sheet.
- `labeler` — your name, same spelling every round

Leave everything else alone, especially `chunk_id`. That's what the merge joins
on, and an edited id silently drops the row.

Judge the text in front of you against `definition.md`. Don't look up the rest of
the code or the jurisdiction, and don't check what anyone else said. Fines'
annotators worked under the same restriction, which is what makes the numbers
comparable.

`unsure` is a real answer. Use it rather than guessing, and write why in `notes`.

### 4. Labelers: hand it back

File, Download, Comma-separated values. Send the coordinator the CSV. Name it
`label_sheet_<yourname>.csv` if the download didn't already.

### 5. Coordinator: merge

Put every file in `labels/`, then:

```bash
python merge_labels.py
```

You get:

- `labels/merged.csv` — one row per chunk, each person's call side by side, plus the majority
- `labels/disagreements.csv` — the rows to talk through, least agreed first
- `labels/keyword_scores.csv` — per keyword: rows labeled, how many the group called commerce, and the share

It prints Fleiss' kappa for `is_commerce` and `category`, computed over rows
every labeler covered. Fines reported 0.66 to 0.86 on their fields, so that's the
range to compare against. Low kappa means `definition.md` is unclear, not that
someone was careless.

### 6. Everyone: talk through the disagreements

Walk `disagreements.csv` together. Every resolved case turns into either a line
in `definition.md` or an entry in the edge-case log. That editing is the actual
deliverable; the labels are how we find out what needs editing.

### 7. Coordinator: commit the round

```bash
git add labels/ definition.md commerce_keywords.txt
git commit -m "Round 1: 3 labelers, 150 rows, kappa 0.xx; dropped 'sign' (0.xx precision)"
```

Commit the filled-in label files, not `out/`. The commit message is where the
round's numbers live, so write them in.

Then prune `commerce_keywords.txt` using `keyword_scores.csv`, and say in the
commit why each word went.

## Notes

Rounds get smaller. The first one is about finding out where the definition is
vague. Later ones sample from the parts we got wrong.

If someone relabels a few rows after the discussion, they resend the whole file
and the coordinator replaces it. Never hand-edit a file in `labels/`.

Once we have a few hundred labeled rows, they become training data for a
classifier, and the keyword list stops being how we find commerce.
