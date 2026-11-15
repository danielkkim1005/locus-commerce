"""Inter-annotator agreement statistics.

These were spread across three files - `fleiss_kappa` and `majority` in
merge_labels.py, `gwet_ac1` in merge_round2.py, `cohen_kappa` in
llm_ablation.py - with each importing from whichever file happened to define
the one it needed. One module instead, so a change to a statistic changes it
everywhere and a round's numbers can be reproduced from a single place.

Two statistics are always reported together. Fleiss' kappa is what round 1
reported and what LOCUS-Fines reported, so it is the comparison. But kappa
collapses toward zero when one category takes almost every rating, and in a
stratified sheet that is a property of the sample rather than of the labelers:
round 1's business slice gave kappa 0.06 at 53% identical answers. Gwet's AC1
does not have that behaviour, so a large kappa/AC1 gap is itself a finding - it
says the labelers agree but the sheet is lopsided.

`items` throughout is one list per row, holding that row's ratings in a fixed
labeler order; `categories` is the closed list those ratings are drawn from.
"""


def majority(values: list[str]) -> tuple[str, bool]:
    """Modal value and whether it was unanimous. Ties return "tie"."""
    if not values:
        return "", False
    counts: dict[str, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    top = max(counts.values())
    winners = [v for v, n in counts.items() if n == top]
    if len(winners) > 1:
        return "tie", False
    return winners[0], top == len(values)


def fleiss_kappa(items: list[list[str]], categories: list[str]) -> float | None:
    """Fleiss' kappa over items rated by the same number of raters.

    Observed agreement is the mean per-item share of agreeing rater pairs;
    expected agreement is the sum of squared category marginals. Returns None
    when there is nothing to compute, or when expected agreement is 1 (every
    rating in one category), where the statistic is undefined rather than zero.
    """
    items = [i for i in items if len(i) == len(items[0])] if items else []
    n = len(items[0]) if items else 0
    if not items or n < 2:
        return None
    idx = {c: j for j, c in enumerate(categories)}
    k, N = len(categories), len(items)
    if k < 2:
        return None

    totals = [0] * k
    agree = []
    for ratings in items:
        counts = [0] * k
        for r in ratings:
            if r not in idx:
                return None
            counts[idx[r]] += 1
        for j in range(k):
            totals[j] += counts[j]
        agree.append((sum(c * c for c in counts) - n) / (n * (n - 1)))
    p = [t / (N * n) for t in totals]
    p_a = sum(agree) / N
    p_e = sum(x * x for x in p)
    if p_e >= 1:
        return None
    return (p_a - p_e) / (1 - p_e)


def gwet_ac1(items: list[list[str]], categories: list[str]) -> float | None:
    """Gwet's AC1. Same inputs as fleiss_kappa.

    Identical observed agreement; the chance term is
    (1/(k-1)) * sum_j pi_j (1 - pi_j), which does not blow up when one category
    takes almost every rating the way Fleiss' sum of squared marginals does.
    """
    items = [i for i in items if len(i) == len(items[0])] if items else []
    n = len(items[0]) if items else 0
    if not items or n < 2:
        return None
    k = len(categories)
    if k < 2:
        return None
    idx = {c: j for j, c in enumerate(categories)}
    N = len(items)

    pi = [0.0] * k
    agree = []
    for ratings in items:
        counts = [0] * k
        for r in ratings:
            counts[idx[r]] += 1
        for j in range(k):
            pi[j] += counts[j]
        agree.append((sum(c * c for c in counts) - n) / (n * (n - 1)))
    pi = [v / (N * n) for v in pi]
    p_a = sum(agree) / N
    p_e = sum(x * (1 - x) for x in pi) / (k - 1)
    if p_e >= 1:
        return None
    return (p_a - p_e) / (1 - p_e)


def cohen_kappa(pairs: list[tuple[str, str]], categories: list[str]) -> float | None:
    """Two raters over the same items.

    Fleiss on two raters is Cohen's up to rounding; this is written out so the
    pairwise comparisons - labeler against labeler, or a model against the
    human majority - read plainly at the call site.
    """
    pairs = [(a, b) for a, b in pairs if a in categories and b in categories]
    n = len(pairs)
    if n < 2:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    pe = 0.0
    for c in categories:
        pa = sum(1 for a, _ in pairs if a == c) / n
        pb = sum(1 for _, b in pairs if b == c) / n
        pe += pa * pb
    if pe >= 1:
        return None
    return (po - pe) / (1 - pe)


def collapse(items: list[list[str]], mapping: dict[str, str],
             categories: list[str]) -> tuple[list[list[str]], list[str]]:
    """Remap every rating, returning the new items and category list.

    Used for sensitivity analysis on a coding scheme rather than on the labels:
    merging two values raises observed agreement and the chance term together,
    so kappa can move either way, which is what makes the comparison
    informative. Values absent from the mapping pass through unchanged.
    """
    out = [[mapping.get(v, v) for v in row] for row in items]
    seen: list[str] = []
    for c in categories:
        m = mapping.get(c, c)
        if m not in seen:
            seen.append(m)
    return out, seen


def unanimous_rows(items: list[list[str]]) -> int:
    """How many rows every rater rated identically."""
    return sum(1 for row in items if len(set(row)) == 1)


def fmt(v: float | None) -> str:
    return "n/a" if v is None else f"{v:+.3f}"


def both(items: list[list[str]], categories: list[str]) -> str:
    """Kappa and AC1 side by side, for a report line."""
    if not items:
        return "n=0"
    return (f"kappa {fmt(fleiss_kappa(items, categories)):>7}   "
            f"AC1 {fmt(gwet_ac1(items, categories)):>7}   (n={len(items)})")
