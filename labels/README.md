Filled-in label sheets, one per person per round. These are inputs: they are
what someone actually typed, and nothing in the repo regenerates them.

    round<N>_<name>.csv       round 2 onward
    label_sheet_<name>.csv    round 1

Identity comes from the filename, never from the `labeler` column inside the
file. Round 1 took it from the column and one person spelled their own name two
ways, which split them into two phantom annotators and made kappa undefined.

Derived files — merged, disagreements, keyword scores, summaries — live in
`results/round<N>/`. Nothing here is written by a script.
