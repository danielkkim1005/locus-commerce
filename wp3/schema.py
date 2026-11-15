"""The label schema, in one place, for every round.

Before this module the coded value lists lived in three files at once -
make_sheets.py, merge_round2.py and llm_ablation.py - and they had already
drifted apart. make_sheets.py still offered `truncated` in the `unresolvable`
dropdown and steps 1-5 in the `step` dropdown, both of which codebook v3
removed, so the next round's sheets would have collected values the merge no
longer recognises.

A schema that must agree with `codebook/v3.md` should be stated once. Anything
that reads or writes a label cell imports it from here.

Round 1 used a different schema and its labels are still in the repo, so its
value lists stay too, marked legacy. Nothing new should use them.
"""

# ---------------------------------------------------------------- round 2 / 3

TIERS = ["core", "adjacent", "not"]

ADJACENT_REASONS = ["gov-market", "revenue", "land-use", "general-law",
                    "counterparty", "procedure", "definition", "sometimes-business"]

CATEGORIES = ["entry", "operation", "exit", "other"]

CONFIDENCE = ["High", "Medium", "Low"]

# The four-way outcome the merge scores: a tier, or an abstention. An
# `unresolvable` call is an answer step 1 asks for, not a missing label, so it
# belongs in the same column as the tiers when agreement is computed.
OUTCOMES = TIERS + ["unresolvable"]


def unresolvable_values(version: int = 3) -> list[str]:
    """Allowed `unresolvable` codes for a codebook version.

    v2 had two: `truncated` (the chunk is cut mid-provision) and `no-context`
    (the chunk never names its own subject). Round 2 measured them and they are
    not the same thing: 33 of 75 chunks had a broken boundary and 31 of those
    were judged on the merits anyway, while 4 of the 5 rows one labeler called
    unresolvable had clean boundaries. Truncation is also mechanically
    decidable, so three people disagreeing about it eight times was measurement
    error by construction, worth 0.050 of the headline figure.

    v3 therefore computes truncation at export and leaves `no-context` as the
    only human-set value. Reading round-2 sheets still needs the v2 list.
    """
    return ["truncated", "no-context"] if version <= 2 else ["no-context"]


def steps(version: int = 3) -> list[str]:
    """Allowed `step` values for a codebook version.

    v3 merged v2's steps 2 and 3. Of the 40 round-2 rows where all three
    labelers gave the identical answer, 13 carried different step numbers, and
    every one was a 2-vs-3 split on a `not` row; merging takes that to zero,
    while merging 4 and 5 instead leaves it at 13 with kappa flat.
    """
    return ["1", "2", "3", "4", "5"] if version <= 2 else ["1", "2", "3", "4"]


# v2 step number -> v3 step number. Applied so round-2 step data stays
# comparable with round 3 rather than being thrown away.
STEP_V2_TO_V3 = {"1": "1", "2": "2", "3": "2", "4": "3", "5": "4"}


def coded_columns(version: int = 3) -> dict[str, list[str]]:
    """Every closed-list column and its allowed values, for one codebook version."""
    return {
        "tier": TIERS,
        "adjacent_reason": ADJACENT_REASONS,
        "category": CATEGORIES,
        "unresolvable": unresolvable_values(version),
        "step": steps(version),
        "confidence": CONFIDENCE,
    }


# ------------------------------------------------------------ round 1, legacy

LEGACY_COMMERCE = ["yes", "no", "unsure"]
LEGACY_CATEGORIES = ["entry", "operation", "exit", "other"]

# Round 1 collected every cell as free text, which cost a normalizer per field.
# make_sheets.py and its dropdowns exist because of this.
LEGACY_YES = {"yes", "y", "true", "1", "t"}
LEGACY_NO = {"no", "n", "false", "0", "f"}
LEGACY_UNSURE = {"unsure", "u", "maybe", "?", "idk"}
LEGACY_NOT_A_CATEGORY = {"", "n/a", "na", "none", "unsure", "?", "idk", "tbd"}
