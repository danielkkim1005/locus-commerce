# WP3 Commerce — LLM ablation results

Codebook v3 run through `gemini-3.5-flash-lite` in five prompt variants, scored
against the hand-labeled rounds. Run Nov 19, 2026. Every number below comes from
`llm_ablation.py` and can be rebuilt from the committed responses with no API key
(see Reproduce). Nothing here is estimated.

Shareable write-up for the team: [WP3 Commerce — LLM Ablation Results and Codebook
Rulings](https://claude.ai/artifact/8QR1CCvcBoqtAK3RDCwJSP). This file is the record
tied to the code and the commit.

## Headline

On round 2 (held out, n=72), the full codebook (E) scores **kappa 0.661** against the
human majority. As a fourth annotator the model leaves Fleiss' kappa unchanged
(0.586 with it, 0.586 without), and its pairwise kappa with each of us (0.55–0.63)
sits inside the human pairwise range (0.49–0.67).

Rows the model answers differently across repeats are rows we split on: 61% vs 32%
of stable rows, Fisher one-sided **p = 0.012**. On its stable rows E is 84% accurate.

The procedure helps the model (B vs A, p = 0.012). The hypothesis that a model gains
more from worked examples than from the procedure is **not supported**: the
contrasts point the other way, though not significantly at n=72.

## Setup

| variant | prompt contains | size |
| --- | --- | --- |
| A | core test only | ~1.0k tokens |
| B | A + four-step procedure | ~1.5k |
| C | B + reason codes with carve-outs (= E minus examples) | ~2.5k |
| D | E minus the procedure | ~3.9k |
| E | full codebook | ~4.5k |

Model `gemini-3.5-flash-lite`, OpenAI-compatible endpoint, temperature 0.7,
`--reasoning-effort minimal`, reasoning emitted before the label. Reason codes and
examples are shuffled per repeat under a seeded RNG (seed 71). Model labels live in
their own column and never enter a human one.

- **Round 1** (development): 60 rows with at least two labelers and no `unsure`,
  scored as core vs everything else, 3 repeats, 900 calls. A proxy only: round 1
  asked yes/no, not the three-tier question.
- **Round 2** (held-out test): 72 rows with a human majority (r16, r19, r20 tied and
  dropped), 5 repeats, 1,800 calls. Run once.

## Round 2 — accuracy against the human majority

| variant | acc | kappa | F1 core | F1 adjacent | F1 not | F1 unresolvable |
| --- | --- | --- | --- | --- | --- | --- |
| A | 0.625 | 0.481 | 0.76 | 0.34 | 0.74 | 0.29 |
| B | 0.750 | 0.643 | 0.82 | 0.58 | 0.87 | 0.29 |
| C | 0.736 | 0.636 | 0.88 | 0.61 | 0.82 | 0.29 |
| D | 0.667 | 0.553 | 0.82 | 0.47 | 0.83 | 0.29 |
| E | 0.750 | **0.661** | 0.90 | 0.56 | 0.88 | 0.40 |

Parse rate 100% for every variant; abstention 3–4%.

## Contrasts

One row is 0.014 accuracy, so each contrast is tested on the rows where the two
variants disagree (exact two-sided McNemar).

| contrast | measures | won / lost | p |
| --- | --- | --- | --- |
| B − A | the procedure, on a bare definition | 10 / 1 | **0.012** |
| E − D | the procedure, on the full codebook | 7 / 1 | 0.070 |
| C − D | examples vs procedure, each removed from E | 6 / 1 | 0.125 |
| E − C | the worked examples | 4 / 3 | 1.000 |
| C − B | the reason codes | 3 / 4 | 1.000 |

Length does not explain the C–D gap: D is the longer prompt and does worse.

## Instability as an ambiguity detector

| variant | unstable rows | humans split: unstable / stable | Fisher p | acc stable | acc unstable |
| --- | --- | --- | --- | --- | --- |
| C | 18 / 72 | 0.61 / 0.39 | 0.086 | 0.83 (54) | 0.44 (18) |
| D | 22 / 72 | 0.64 / 0.36 | **0.028** | 0.84 (50) | 0.27 (22) |
| E | 21 / 72 | 0.57 / 0.39 | 0.129 | 0.84 (51) | 0.52 (21) |
| any of C, D, E | 31 / 72 | 0.61 / 0.32 | **0.012** | | |

Base human split rate: 0.44. E on its stable rows, excluding human-unresolvable gold:
0.93 (44 rows).

A and B never vary: nothing in their prompts is shuffled. The instability in C–E is
sensitivity to the order of reason codes and examples, not temperature noise; report
it that way.

## Model as a fourth annotator (E, modal answer)

| pair | kappa |
| --- | --- |
| model – daniel | 0.630 |
| model – sachin | 0.593 |
| model – ainesh | 0.551 |
| ainesh – sachin | 0.674 |
| daniel – sachin | 0.596 |
| ainesh – daniel | 0.491 |

Fleiss 4-way 0.586 (AC1 0.607), humans only 0.586. The humans-only figure exceeds the
published 0.549 because the three tied rows are dropped here.

## Errors

Almost every miss is an `adjacent` answer. E's 18 errors: 8 human-unresolvable rows
called adjacent, 6 not → adjacent, 3 core → adjacent, 1 unresolvable → core. D has
the same shape. This is the same boundary that carried 14 of 15 human tier splits
in round 2.

Round 1 scores the reason-code variants lower (C 0.75 vs A 0.95) because round 1's
yes counted licensing procedure and fees that v3 places in `adjacent`. That is the
proxy disagreeing with the codebook, not a prompt defect; no prompt was changed
between round 1 and round 2.

## Codebook rulings (group, Nov 2026)

| question | ruling |
| --- | --- |
| Does `adjacent` ship? | Yes. Tier stays ternary: core / adjacent / not. |
| Unreadable rows, running headers | `unresolvable` folds into tier as a fourth value (tier is empty whenever it is set). Expected to become rare with LOCUS-v2's cleaner OCR. v3's header rule unchanged. |
| Entry vs operation for permits | Decides whether you hold the authorization (issuance, duration, renewal) → entry; losing it → exit; conduct while holding it → operation. Hard to test at this n; expected to generalize. |
| Unresolvable vs tier disagreements | Report both (0.549 as disagreement; 0.599 / 0.724 with exclusions) and justify the higher figure in the paper. |

## Caveats

One model, at minimal reasoning effort. 72 test rows. Gold from three undergraduate
labelers. The unresolvable class is too small to judge. Round 1's text was cut at
2,000 characters by the round-1 export.

Harness bugs found and fixed before the round-2 run, none of which touched round 2:
round-1 text read from the wrong column; `y`/`n` answers dropped; adjacent answers
mis-scored in binary mode.

## Reproduce

```bash
# rebuild every table above from the committed responses (no key, no calls)
python llm_ablation.py --eval round2 --repeats 5 --from-runs labels/llm_runs.csv

# the original runs
export OPENAI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai"
python llm_ablation.py --backend openai --model gemini-3.5-flash-lite \
    --reasoning-effort minimal --sleep 0.5 --eval round1 --repeats 3
python llm_ablation.py --backend openai --model gemini-3.5-flash-lite \
    --reasoning-effort minimal --sleep 0.5 --eval round2 --repeats 5
```

`labels/llm_runs.csv` holds every round-2 response; `labels/llm_rowstats.csv` the
per-row modal answer and stability; `labels/llm_ablation.txt` the printed summary.
The API cache (`out/llm_cache/`) is gitignored.
