"""Reading label sheets: who wrote them, and what a cell means.

There were four versions of `labeler_name` in this repo and two verbatim copies
of the round-1 normalizers. One copy each, here.
"""

import csv
import pathlib

from . import schema

# Files that live in a labels directory but are not someone's labels. The merge
# writes some of these itself, so without the list a second run would read its
# own output back in as a fourth annotator.
DERIVED = {
    "merged.csv", "disagreements.csv", "keyword_scores.csv", "round1_summary.txt",
    "round1_clean.csv", "discussion_queue.csv",
    "round2_merged.csv", "round2_disagreements.csv", "round2_keyword_scores.csv",
    "round2_summary.txt", "llm_runs.csv", "llm_rowstats.csv", "llm_ablation.txt",
}

_PREFIXES = ("round3_", "round2_", "round1_", "label_sheet_", "labels_")


def labeler_name(path: pathlib.Path) -> str:
    """One identity per FILE, never per cell.

    Round 1 took the name from a free-text `labeler` column, and one person
    spelled it two ways across their own sheet. The merge then saw four
    annotators where there were three, every row was missing at least one of
    them, and kappa came out None. The column can drift; the filename cannot.

        labels/round2_sachin.csv                      -> sachin
        labels/label_sheet_daniel - label_sheet.csv   -> daniel
    """
    stem = path.stem
    for prefix in _PREFIXES:
        if stem.startswith(prefix):
            stem = stem[len(prefix):]
            break
    return (stem.split(" - ")[0].strip() or path.stem).lower()


def sheet_files(ldir: pathlib.Path, round_no: int) -> list[pathlib.Path]:
    """The human-written sheets for one round, derived files excluded."""
    pattern = "label_sheet_*.csv" if round_no == 1 else f"round{round_no}_*.csv"
    return sorted(p for p in ldir.glob(pattern) if p.name not in DERIVED)


def norm_coded(field: str, raw: str, allowed: dict[str, list[str]]
               ) -> tuple[str | None, str | None]:
    """Normalize one closed-list cell. Returns (value, off_list_raw).

    Blank is ignored rather than counted as a judgment. For `tier` a blank is
    usually not unfinished work: step 1 says to set `unresolvable` and leave
    `tier` empty when the chunk never names what it governs.

    An off-list value is reported rather than silently dropped. The dropdowns in
    make_sheets.py mean the cells should already be clean, so a value that
    escaped validation means someone typed around it, and that is worth seeing.
    """
    v = (raw or "").strip().lower()
    if not v:
        return None, None
    for candidate in allowed[field]:
        if v == candidate.lower():
            return candidate if field == "confidence" else v, None
    return None, (raw or "").strip()


def norm_legacy_commerce(raw: str) -> str | None:
    """Round 1's free-text `is_commerce` cell."""
    v = (raw or "").strip().lower()
    if v in schema.LEGACY_YES:
        return "yes"
    if v in schema.LEGACY_NO:
        return "no"
    if v in schema.LEGACY_UNSURE:
        return "unsure"
    return None


def norm_legacy_category(raw: str) -> str | None:
    """Round 1's free-text `category` cell, which could hold several values.

    Cells came back as "operations", "entry & operation", "n/a". Untreated,
    each distinct string counted as its own category and the statistic measured
    spelling. Multi-valued cells are kept as a sorted comma-joined string so the
    merge can report agreement with and without them.
    """
    v = (raw or "").strip().lower()
    if v in schema.LEGACY_NOT_A_CATEGORY:
        return None
    found = [c for c in schema.LEGACY_CATEGORIES if c in v]  # 'operations' holds 'operation'
    if not found:
        return None
    return ",".join(sorted(found))


def read_rows(path: pathlib.Path):
    """Rows of a sheet, BOM-tolerant. Drive exports carry a UTF-8 BOM."""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        yield from csv.DictReader(fh)
