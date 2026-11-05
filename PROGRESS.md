# PROGRESS.md: Ingredient Drift Radar

Last updated: 2026-11-05
Current position: Phase 2, Steps 1 and 2 done. Next: Step 3 (manifest in DuckDB), Step 4 (idempotent incremental fetcher), Step 5 (contingency cohort ingest).

## Project in one paragraph

A data engineering portfolio project on Open Food Facts (OFF): a revision-aware pipeline that preserves product revisions, separates human edits from bot edits and system recomputation, classifies each record change, and surfaces evidence-backed candidates for human review. Planned stack: Python ingestion, Spark (large catalogue processing), Delta Lake, dbt, Airflow, GitHub Actions. Constraints: 12 GB RAM laptop, zero budget (free tools and free tiers only), 4 to 5 month timeline.

Honesty rule: OFF is community-edited. We detect changed records, not proven recipe changes. Never overclaim in alerts, docs or interviews.

## Working agreement with the mentor chat

- State the phase and step every session.
- Teach each tool and design choice (what, why over alternatives, how it fits).
- Small runnable steps, plain text answers, code in code blocks.
- Flag cost, RAM and free-tier risks. Say when unsure and tell me to verify.
- Push back on over-scoping, skipped tests and weakened design.
- End each session with an updated PROGRESS.md block.

## Phase status

| Phase | Deliverable | Status |
|---|---|---|
| 1. Data validation | 44-product feasibility cohort, revision retrieval, analysis | Done: GO (reframed claim) |
| 2. Raw storage and ingestion | Raw layout, manifest, idempotent fetcher, contingency cohort | In progress: Steps 1-2 done, Step 3 next |
| 3. Spark processing | Normalise catalogue subset, then scale | Not started |
| 4. Revision modelling | Compare revisions, classify, provenance | Not started (checkpoint here) |
| 5. Delta Lake | Versions and change events | Not started |
| 6. dbt | Marts and tests | Not started |
| 7. Airflow | Orchestration | Not started |
| 8. Tests and CI/CD | pytest, dbt tests, GitHub Actions | Not started |
| 9. Dashboard and alerts | Evidence-backed review | Not started |
| 10. Deployment and docs | Documentation, limitations | Not started |

## Phase 1 results

Setup: repo, minimal Docker (Python only; Spark, Airflow and Delta deferred), `.env` with identifiable User-Agent.

Scripts in `ingestion/`: `probe_revision_api.py`, `select_cohort.py` (DuckDB, in-memory, queries remote Parquet in place), `fetch_revisions.py` (rate-limited at 4.2 s per request, cached and resumable), `analyze_feasibility.py`, `analyze_pairs.py`, `analyze_tags.py`, `check_tag_noise.py`, `diff_fields.py`.

API finding: `?rev=` parameter on the v2 product endpoint returns the requested revision. The static revision file approach did not work and was dropped. Fetch mode: `--mode api`.

Measurements (44 products, 814 consecutive pairs):
- Honoured revisions: 100% of products had at least 2. Missing requests: 0% in the first sampled run.
- Ingredient text pairs: both_missing 456, no_change 299, completion 43, set_change 11, formatting_only 5.
- Allergen tag pairs: same 656, from_empty 29 (25 coincide with completion), added 6, removed 3, not_comparable 120.
- Text comparison: 12/44 products with a candidate; about 4 plausible after manual review; about 1 clear human content edit (3174332018297, rev 14 to 15, saved 7 seconds apart by a new corrector).
- Tag comparison: 62 tag_change pairs in 30/44 products; 52 of 62 had identical ingredient text. Tags are derived data recomputed by OFF, so they are a poor primary evidence source.

Key discoveries:
1. Data completion dominates "change". Early revisions are mostly empty.
2. A revision bundles human-edited source fields and system-derived fields.
3. Provenance is available (`last_modified_by`, `last_editor`, `editors_tags`, `correctors_tags`). Example: rev 18 to 19 of barcode 00071109 was saved by `fix-code-bot`: barcode zero-padded and allergen fields recomputed with unchanged ingredient text.
4. Barcode formatting can change between revisions (071109 to 00071109).
5. Schemas and types drift across years (for example `nova_group` string versus integer).
6. Ingredient text can be polluted (OCR, multilingual, nutrition tables).

## Phase 2 progress

Done (Steps 1 and 2), pushed to GitHub, 31 pytest tests passing (Windows, Python 3.13.1, pytest.ini, requirements.txt, config via .env, .env.example tracked):
- Barcode normalisation: src/ingredient_drift/barcode.py. normalise_barcode(raw) returns BarcodeResult(raw_code, normalised_code, status, check_digit_valid). Status: ok, adjusted, unrecognised_length, invalid_input. Never raises on bad data; check digits are metadata only. Rule confirmed from OFF documentation: after stripping leading zeros, 1-7 digits pad to 8, 9-12 pad to 13; 8 and 13 kept. 14+ digits are our own choice (pass through unchanged).
- Real Phase 1 check: no folders keyed on an unnormalised code; one invalid-check-digit code (14104006) kept and flagged.
- Raw store: src/ingredient_drift/raw_store.py. Layout off_revisions/<normalised_code>/rev_<6 digits>.json.gz. Body stored untouched, gzip mtime=0, atomic write (temp file, fsync, os.replace), refuses overwrite, sha256 of the uncompressed body.
- README added to the repo.

Remaining:
- Step 3: manifest in DuckDB.
- Step 4: idempotent, incremental fetcher (skip stored revisions; fetch only newer than stored max).
- Step 5: contingency cohort (revision range 30 to 120, about 12 sampled revisions each) as the first real ingest.
- Provenance extraction stays a design note until Phase 4 (editor from last_modified_by, else set difference of editors_tags / correctors_tags; documented account-category allowlist).

## Decisions made

Phase 1:
- GO to Phase 2 with a reframed claim: "a revision-aware pipeline that separates human edits from system recomputation, classifies record changes, and surfaces evidence-backed candidates for review". Not "detects ingredient drift".
- `ingredients_text` and user-entered allergen and trace fields are primary evidence. Tags and other derived fields are context only.
- Compare consecutive revisions; consider coalescing revisions seconds apart by the same editor into one edit session (Phase 4 design).
- Local folders first for raw storage; MinIO or S3 only after verifying free-tier limits.
- Kafka, ML and LLMs stay out of v1.

Phase 2:
- Manifest in DuckDB: manifest table (one row per request attempt, append-only, run_id) plus runs table (run_id, start, end, counts per outcome, skipped_count). Skipped revisions are not logged per row.
- Manifest fields: run_id, normalised_barcode, raw_code, revision_requested, request_url, requested_at_utc, http_status, outcome, size_bytes, stored_bytes, sha256, file_path, fetcher_version, user_agent_id.
- Outcomes: stored, not_found, revision_not_honoured, identifier_mismatch, http_error, rate_limited, parse_error.
- Honoured revision = int(product["rev"]) equals revision requested (cast defensively; rev can be str or int).
- Fetcher compares normalise(requested code) with normalise(response code) and records identifier_mismatch (OFF API normalises codes on read).
- Idempotency, testably: after a rerun, raw files and bytes are identical and each (code, revision) has exactly one stored row with matching sha256; only runs rows and retries of earlier failures may differ.
- Single-process sequential fetcher, 4.2 s between requests, HTTP 429 handled with backoff.
- Raw files are gzipped (convenience: data/raw was 19M by du, 17M apparent, 911 files).
- Phase 1 cache (data/raw/revisions: <code>/<rev>.json, .missing markers, current.json; byte-exactness unknown) is a legacy layout. Re-fetch cleanly (about 860 requests, roughly 1 hour) or import with an explicit outcome: decide in Step 4.
- pyproject.toml deferred to Phase 8 at the latest.

Checkpoint at the end of Phase 4: at least 6 reviewed events where a human edit changed ingredient content (not formatting, OCR cleanup or bot re-derivation), counted across the 44-product cohort plus a contingency cohort (revision range 30 to 120, about 12 sampled revisions each). If not met, reframe fully around completion tracking, provenance and data-quality monitoring, with drift as a small, honestly labelled feature.

## Open items

- [ ] Add real-case fixture test for 14104006 (ok, check digit invalid) and a 14-digit leading-zero test (our assumption).
- [ ] Update collapse-test comment to "follows OFF documented rule".
- [ ] Fix README test section (venv, pip install -r requirements.txt, pytest).
- [ ] Verify OFF API rate limit on the docs page myself; check it applies to ?rev= requests; record the date in docs/design_decisions.md.
- [ ] Record the barcode rule source and the three barcode design choices in docs/design_decisions.md.
- [ ] Look at one product's edit history on the OFF website to see the data first-hand.
- [ ] Still open from Phase 1: Parquet export schema and update frequency, ODbL attribution, free-tier limits of Databricks/S3 (not verified so far).

## Scale notes

- Scaling beyond 44 products is possible but bounded by the API rate limit. At one request per 4.2 s, 1,000 products with about 20 revisions each is roughly 20,000 requests, about 23 hours of fetching in total (arithmetic from the stated limit; verify the limit).
- History is stored only for monitored products. Other products are covered by periodic catalogue snapshots; a rise in a product's `rev` between snapshots can promote it to the monitored list. Snapshot comparison at catalogue scale is the intended genuine Spark workload.

## Interview summary (current, honest version)

"I built a revision-aware pipeline on Open Food Facts that preserves product revisions, separates human edits from bot edits and system-recomputed fields, classifies record changes, and produces evidence-backed review candidates. Before building, I ran a feasibility study that showed most apparent changes are data completion or derived-field churn, so the design treats raw ingredient text as primary evidence and never claims a recipe changed."

## Handoff for a new chat

Paste this at the start: "Continue Ingredient Drift Radar. Read PROGRESS.md and source_limitations.md in project knowledge. We are in Phase 2, starting Step 3 (ingestion manifest in DuckDB), then Step 4 (idempotent incremental fetcher). Follow the working agreement in PROGRESS.md. I will paste ingestion/fetch_revisions.py for the rewrite."