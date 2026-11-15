"""Merge a labeling round's sheets and report where we disagreed.

    python merge_round.py --round 2
    python merge_round.py --round 1                 # reproduces round 1's numbers
    python merge_round.py --round 2 --out results/round2

One entry point for every round. The scoring differs by round because the
schema did - round 1 asked a single yes/no/unsure question, round 2 asked for a
tier plus a reason code plus a step - so each round's logic lives in its own
module under `rounds/`. What they share, the agreement statistics and the rule
that a labeler's identity comes from the filename rather than from a free-text
column, lives in `wp3/`.

Adding round 3 means adding `rounds/round3.py` and one line here, not copying a
600-line script and editing the column names.

Outputs land in `results/round<N>/` by default. Inputs in `labels/` are the
sheets people filled in, and nothing here writes to that directory.
"""

import argparse
import importlib
import pathlib

ROUNDS = {1: "rounds.round1", 2: "rounds.round2"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--round", type=int, required=True, choices=sorted(ROUNDS),
                    help="which labeling round to merge")
    ap.add_argument("--labels", default="labels",
                    help="directory holding the filled-in sheets")
    ap.add_argument("--out", default=None,
                    help="where to write merged/disagreements/summary "
                         "(default: results/round<N>)")
    ap.add_argument("--key", default=None,
                    help="round 2 only: out/round2_key.csv, the coordinator-only "
                         "provenance file. Without it the stratum and keyword "
                         "sections are skipped.")
    args = ap.parse_args()

    ldir = pathlib.Path(args.labels)
    outdir = pathlib.Path(args.out) if args.out else pathlib.Path(f"results/round{args.round}")
    outdir.mkdir(parents=True, exist_ok=True)

    module = importlib.import_module(ROUNDS[args.round])
    if args.round == 1:
        module.merge(ldir, outdir)
    else:
        module.merge(ldir, outdir, pathlib.Path(args.key) if args.key else None)


if __name__ == "__main__":
    main()
