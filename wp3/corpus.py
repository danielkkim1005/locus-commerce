"""Corpus-side helpers: the chunk id, the parquet source, the keyword matcher.

Lifted verbatim out of the old export_commerce.py so that the script that
builds the slices and any future script that samples from them share one
definition. The keyword list is a candidate-finder, not the definition of
commerce: nothing counts until a person reads it, which is what keeps a loose
keyword cheap and a missing keyword expensive.

The word-boundary rule here is not cosmetic. Plain substring matching had
`sign` matching "design" and "designated" and `tow` matching "town", which
accounted for 11% of sampled boundary rows before it was caught.
"""

import pathlib
import re

# LOCUS-v1 has no row identifier, so we make a stable one from the row's own
# content. Same row, same id, on anyone's machine. Labels can be joined back on it.
CHUNK_ID = """md5(concat_ws('|', state, coalesce(city, ''), coalesce(county, ''),
                            coalesce(header, ''), coalesce(content, '')))"""

# You do not have to download the 1.8 GB corpus. DuckDB's httpfs extension reads
# the shards straight off the Hub over range requests, and Parquet is columnar, so
# a query only pays for the columns it names: on one shard, scanning header+topic
# takes about a second, scanning content about eight. The dataset is public, so no
# token is needed.
HF_SOURCE = "hf://datasets/LocalLaws/LOCUS-v1/data/train-*.parquet"
REMOTE_SCHEMES = ("hf://", "s3://", "gcs://", "gs://", "az://", "http://", "https://")


def parquet_source(con: "duckdb.DuckDBPyConnection", data: str) -> tuple[str, str]:
    """Resolve --data to (glob for read_parquet, one-line description).

    Accepts a local folder of shards, or any remote path DuckDB can open. Remote
    paths need httpfs, which ships with DuckDB but loads on demand.
    """
    if data.startswith(REMOTE_SCHEMES):
        con.execute("INSTALL httpfs")
        con.execute("LOAD httpfs")
        return data, f"remote: {data}"
    folder = pathlib.Path(data)
    shards = sorted(folder.glob("train-*.parquet"))
    if not shards:
        raise SystemExit(
            f"no parquet shards under {folder.resolve()}\n"
            f"  pass --data if LOCUS-v1 is somewhere else, or\n"
            f"  pass --hf to read the corpus off Hugging Face without downloading it"
        )
    return ((folder / "train-*.parquet").as_posix(),
            f"{len(shards)} local shards under {folder.resolve()}")


def load_keywords(path: pathlib.Path) -> list[str]:
    words = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            words.append(line.lower())
    if not words:
        raise SystemExit(f"no keywords found in {path}")
    return words


def keyword_regex(word: str) -> str:
    """Match on word boundaries, so 'sign' stops matching 'design' and 'assigns'.

    A trailing * means prefix match: 'licens*' catches license, licensing, licensee.
    Without it the whole word must match: 'tow' will not match 'town'.
    """
    stem = word[:-1] if word.endswith("*") else word
    body = re.escape(stem).replace("\\ ", " ")
    return r"\b" + body if word.endswith("*") else r"\b" + body + r"\b"


def sql_list(words: list[str]) -> str:
    """A DuckDB list literal of the patterns. Single quotes doubled; nothing else in."""
    inner = ", ".join("'" + keyword_regex(w).replace("'", "''") + "'" for w in words)
    return "[" + inner + "]"


def sql_labels(words: list[str]) -> str:
    """The keywords as written, in the same order as sql_list, for reporting."""
    inner = ", ".join("'" + w.replace("'", "''") + "'" for w in words)
    return "[" + inner + "]"
