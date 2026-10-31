# DuckDB notes (verified 2026-10-31)

## Version and source

| Item | Value |
|---|---|
| Package | `duckdb` |
| Version | 2.0.0 |
| Release date (PyPI) | 2026-10-21 |
| Python requirement | >=3.11 |
| Docs | <https://duckdb.org/docs/stable/clients/python/overview> |
| Versioned docs used | DuckDB 2.0 docs |
| Checked | 2026-10-31 |

Q1 pins `duckdb==2.0.0` when it adds the dependency.

## Full-text search (BM25)

The `fts` extension provides SQLite-FTS5-like full-text search. It autoloads on
first use, or load it explicitly:

```sql
INSTALL AND LOAD fts;
```

Build an index:

```sql
PRAGMA create_fts_index(
  'complaints',
  'id',
  'narrative',
  stemmer = 'porter',
  stopwords = 'english',
  ignore = '(\\.|[^a-z])+',
  strip_accents = 1,
  lower = 1,
  overwrite = 0
);
```

Search with the generated `match_bm25` macro:

```sql
SELECT id, narrative, score
FROM (
  SELECT *, fts_main_complaints.match_bm25(id, 'intermittent wiper') AS score
  FROM complaints
) sq
WHERE score IS NOT NULL
ORDER BY score DESC, id ASC
LIMIT 20;
```

`match_bm25(input_id, query_string, fields := NULL, k := 1.2, b := 0.75,
conjunctive := 0)` returns a score (or `NULL` when the document does not match).
The project rounds scores to 4 decimals and breaks ties by id (PLAN §8).

Important: by default the index does **not** update when the table changes.
Create with `incremental = 1` (requires the id column `NOT NULL` / primary key)
or rebuild the index after loading. Q1/Q2 derive immutable tables, so a
one-time index build is enough; rebuild deterministically after any reload.

## Reading NHTSA tab-delimited files

NHTSA flat files are tab-delimited with a header row and quoted text fields.
Read them explicitly instead of relying on the sniffer:

```sql
CREATE TABLE complaints AS
SELECT *
FROM read_csv(
  'data/raw/COMPLAINTS_RECEIVED_2020-2024.txt',
  delim = '\t',
  header = true,
  quote = '"',
  escape = '"',
  auto_detect = true
);
```

For files whose inferred types are unstable, either keep everything as text and
cast explicitly, or declare the columns:

```sql
SELECT *
FROM read_csv(
  'data/raw/COMPLAINTS_RECEIVED_2020-2024.txt',
  delim = '\t',
  header = true,
  all_varchar = true
);
```

`read_csv` supports `delim`, `header`, `quote`, `escape`, `columns`,
`all_varchar`, `null_padding`, `ignore_errors`, `store_rejects`, and compressed
inputs (`.gz`, `.zst`). Prefer explicit options and fail loudly; do not silently
drop rows. Use `union_by_name = true` when reading several files whose column
order may differ. A malformed row is a data error for Q1 to report, not to hide.

## Writing parquet (zstd)

```sql
COPY (
  SELECT *
  FROM complaints
  ORDER BY id
) TO 'data/kb_complaints.parquet'
(FORMAT parquet, COMPRESSION zstd);
```

Parquet options include `COMPRESSION` (`snappy` default, `zstd`, `gzip`, ...),
`COMPRESSION_LEVEL` (zstd 1-22, default 3), `ROW_GROUP_SIZE`, and
`ROW_GROUP_SIZE_BYTES`. Use zstd for the committed derived files. `COPY ... TO`
overwrites an existing destination safely by writing a temporary file first
(`USE_TMP_FILE` defaults to auto). Read back with:

```sql
SELECT * FROM read_parquet('data/kb_complaints.parquet');
```

To keep `make all` byte-identical (PLAN §8), Q1 should sort every export by a
stable key, set `threads = 1` and `preserve_insertion_order = true` for export
connections, and avoid embedding timestamps or absolute paths in parquet
metadata. That reproducibility recipe is a project decision, not a claim from
the DuckDB docs.

## Python client

```python
import duckdb

con = duckdb.connect("data/field_quality.duckdb")
con.execute("SET threads = 1")
con.execute("SET preserve_insertion_order = true")
rows = con.execute("SELECT count(*) FROM complaints").fetchone()
```

Use one connection per process; the API is synchronous. Q1 owns the schema,
ingest and derived file layout; Q2 reads the committed parquet/DuckDB file and
must not rebuild it.
