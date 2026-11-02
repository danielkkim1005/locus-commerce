# WP3 Commerce — round 2 results

Labeled against `definition_v2.md` (three tiers, 5-step decision procedure,
8 adjacent reason codes). Sheet: 75 rows, seed 71, round-1 chunks held out.
Strata: business 30, boundary 30, random 15.

Labelers: ainesh, daniel, sachin. Sheets in `locus-commerce/labels/round2_*.csv`.
All numbers below come from `python merge_round2.py`, reproduced in
`labels/round2_summary.txt`. Nothing here is estimated.

## Headline

**kappa 0.555, AC1 0.579, n=74** — tier and `unresolvable` together, every row.

Round 1 was kappa 0.232 on `is_commerce` (n=97). Agreement roughly doubled.

Not a like-for-like comparison: round 2 is a different sample, holds out round 1's
chunks, and asks a three-tier question instead of yes/no. The definition rewrite is
the plausible cause, not a proven one.

## Agreement ladder

Each row drops more of the sheet. The gaps are the diagnosis.

| rows kept | excluded | kappa | AC1 | n |
| --- | --- | --- | --- | --- |
| all | self-contradicting cells only | **0.555** | 0.579 | 74 |
| no `truncated` | 8 rows anyone called cut off | 0.607 | 0.637 | 66 |
| no `unresolvable` | 21 legibility-split rows | 0.724 | 0.748 | 52 |

Core vs rest (nearest equivalent to round 1's yes/no): 0.724 / AC1 0.761, n=52.

Of the 0.169 gap between 0.555 and 0.724, about a third is `truncated` — LOCUS chunk
boundaries, which we can describe but not fix. The rest is `no-context`: disagreement
about how much a chunk must name before it is labelable. That part is our wording.

Other fields:

| field | kappa | AC1 | n | note |
| --- | --- | --- | --- | --- |
| adjacent_reason | 1.000 | 1.000 | 3 | n too small to mean anything |
| category | 0.311 | 0.574 | 17 | round 1: 0.509 / 0.567. n too small to compare |
| step | 0.440 | 0.539 | 75 | same tier reached by different routes |

Two statistics throughout. Fleiss' kappa is what round 1 reported, so it is the
comparison. Gwet's AC1 does not collapse when one category dominates, which in a
stratified sheet is a property of the sample. A large kappa/AC1 gap means the
labelers agree but the sheet is lopsided — see `category`.

## Finding 1 — the disagreement is about legibility, not commerce

21 of 75 rows had someone code `unresolvable` while someone else assigned a tier.

| | no-context | truncated | total |
| --- | --- | --- | --- |
| ainesh | 8 | 5 | 13 |
| daniel | 5 | 0 | 5 |
| sachin | 11 | 6 | 17 |

Daniel never used `truncated`; ainesh and sachin used it 11 times across 8 rows
(r22, r33, r38, r40, r49, r50, r51, r59). None of those is the one row our export
actually cut at 6000 chars (r61), so nobody confused the export flag with a real
chunk boundary — these are genuine mid-provision cutoffs in LOCUS that one labeler
read through and two stopped at.

Step 1 says set `unresolvable` when the text "never names the activity or party it
governs" but does not say how much naming is enough. Three people drew that line in
three places. Nothing about commerce is in dispute on these rows.

Cheapest fix available: one worked example in step 1 of a cutoff chunk we *do* label.

## Finding 2 — `adjacent` is the remaining fault line

15 rows had a genuine tier split. **14 of 15 involve `adjacent`.**

| split | rows |
| --- | --- |
| adjacent / adjacent / core | 6 |
| adjacent / core / core | 2 |
| adjacent / not / not | 2 |
| adjacent / core / not | 1 |
| adjacent / adjacent / not | 1 |
| adjacent / core (one blank) | 1 |
| adjacent / not (one blank) | 1 |
| core / not / not | 1 |

Only one disagreement is core-vs-not with no adjacent involved. The core/not boundary
that round 1 could not agree on is largely settled; the open question is now "conduct
rule, or adjacent for one of eight reasons".

Where all three said adjacent, they chose the same reason code every time (3 rows).

Reason codes, counting every labeler's cell and then majority calls only:

| code | cells | majority |
| --- | --- | --- |
| revenue | 10 | 5 |
| land-use | 10 | 3 |
| procedure | 8 | 4 |
| definition | 4 | 1 |
| gov-market | 2 | 0 |
| counterparty | 2 | 1 |
| general-law | 1 | 0 |
| sometimes-business | 1 | 0 |

Plus 3 rows where the majority reason tied. All eight codes were used at least once,
so none is dead, but majority calls concentrate in four: revenue, procedure,
land-use, definition. `sometimes-business` was provisional on one round-1 row and has
one round-2 cell — still unproven.

Maps onto open questions 1/2 (fees vs taxes), 7 (procedure, definitions),
3/4 (land use, signs).

## Finding 3 — same answers, different routes

Which step decided the call:

| | s1 | s2 | s3 | s4 | s5 |
| --- | --- | --- | --- | --- | --- |
| ainesh | 13 | 19 | 8 | 1 | 34 |
| daniel | 6 | 10 | **17** | 1 | 41 |
| sachin | 17 | **26** | 2 | 0 | 30 |

Step kappa 0.440 while tier kappa is 0.724 — people reach the same tier along
different paths. Daniel resolves 17 rows at step 3 ("would a non-commercial actor
doing the same thing be bound?"); sachin resolves 2 there and 26 at step 2 ("is any
commercial subject named?").

The procedure is meant to be the definition's mechanism. Where it is bypassed it is
decorative, and where the paths diverge we cannot predict the outcome.

Step 4 fired twice in 225 labeler-rows. Near dead weight.

## Tier rates by labeler

| | core | adjacent | not | unresolvable | tiered |
| --- | --- | --- | --- | --- | --- |
| ainesh | 22 (35%) | 13 (21%) | 27 (44%) | 13 | 62/75 |
| daniel | 28 (41%) | 14 (20%) | 27 (39%) | 5 | 69/75 |
| sachin | 19 (33%) | 11 (19%) | 28 (48%) | 17 | 58/75 |

Round 1's yes-rate spread was ainesh 47%, daniel 52%, sachin 85%. The outlier is gone.
The remaining spread is in `unresolvable` (5 to 17), i.e. finding 1.

## Tier by stratum, majority call

| stratum | core | adjacent | not | tie |
| --- | --- | --- | --- | --- |
| business (30) | 19 | 9 | 1 | 1 |
| boundary (29) | 4 | 5 | 18 | 2 |
| random (15) | 1 | 3 | 11 | 0 |

`topic == 'Business'` is mostly core, as expected. The boundary slice is mostly not
core — 4/29, against round 1's boundary yes-rate of 17/48. Either the keyword catch
is noisier than round 1 suggested, or v2's narrower `core` excludes what round 1
counted as commerce. Worth settling before the slice is defended in the paper.

## Keyword evidence

From `labels/round2_keyword_scores.csv`, share of each keyword's rows whose majority
call was `core`:

| keyword | rows | core | share |
| --- | --- | --- | --- |
| permit* | 16 | 0 | 0.00 |
| sign* | 4 | 1 | 0.25 |
| revocation | 2 | 0 | 0.00 |
| licens* | 1 | 1 | 1.00 |
| short-term rental* | 1 | 1 | 1.00 |
| sanitation | 1 | 1 | 1.00 |
| bed and breakfast | 1 | 1 | 1.00 |
| inspection*, suspension, business*, alcoholic, beverage*, noise, kennel* | 1 each | 0 | 0.00 |

`permit*` and `sign*` were the two suspects named in the keyword policy. Both confirmed,
`permit*` the higher-volume offender at 0 of 16. Caveat: boundary rows are mostly
not-core anyway, so all keyword precision here is low — `permit*` is the worst at the
largest n.

## Data quality

- Zero off-list values across 225 labeler-rows. The `make_sheets.py` dropdowns worked.
- One self-contradiction: daniel r23 set both `unresolvable` (`no-context`) and a tier
  (`not`). Both cells are dropped from every statistic — step 1 says an unresolvable
  chunk gets no tier, and preferring one cell would be choosing his answer for him.
  Raw values stay in `round2_merged.csv`, with `excluded = daniel`. This is why n=74
  and not 75.
- No blank cell lacked an `unresolvable` code: all 35 untiered cells are step-1 answers,
  not unfinished work.

## Next steps, in order

1. Tighten step 1 with a worked example of a cutoff chunk we do label. Biggest single
   lever on the headline number.
2. Work the 21 legibility-split rows as the discussion queue, ahead of the 15 tier rows.
3. Prune `permit*` from `commerce_keywords.txt`, citing 0/16 in the commit message.
4. Have daniel re-answer r23.
5. Leave `category` alone until n is larger.

## Reproduce

```
cd locus-commerce
python merge_round2.py          # reads labels/round2_*.csv and out/round2_key.csv
```

Writes `labels/round2_merged.csv`, `round2_disagreements.csv`,
`round2_keyword_scores.csv`, `round2_summary.txt`.

`out/round2_key.csv` is coordinator-only — it carries the stratum, state and keyword
columns the sheets withheld. Without it the script still runs; the stratum and keyword
sections are skipped.
