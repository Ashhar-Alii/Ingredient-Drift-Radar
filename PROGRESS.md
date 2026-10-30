# PROGRESS.md: Ingredient Drift Radar

Last updated: 2026-10-31
Current position: Phase 1 complete. Next: Phase 2 (raw storage and ingestion manifest).

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
| 2. Raw storage and ingestion | Raw layout, manifest, idempotent fetcher, contingency cohort | Next |
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

## Decisions made

- GO to Phase 2 with a reframed claim: "a revision-aware pipeline that separates human edits from system recomputation, classifies record changes, and surfaces evidence-backed candidates for review". Not "detects ingredient drift".
- `ingredients_text` and user-entered allergen and trace fields are primary evidence. Tags and other derived fields are context only.
- Compare consecutive revisions; consider coalescing revisions seconds apart by the same editor into one edit session (Phase 4 design).
- Local folders first for raw storage; MinIO or S3 only after verifying free-tier limits.
- Kafka, ML and LLMs stay out of v1.

Checkpoint at the end of Phase 4: at least 6 reviewed events where a human edit changed ingredient content (not formatting, OCR cleanup or bot re-derivation), counted across the 44-product cohort plus a contingency cohort (revision range 30 to 120, about 12 sampled revisions each). If not met, reframe fully around completion tracking, provenance and data-quality monitoring, with drift as a small, honestly labelled feature.

## Open items (do before or early in Phase 2)

- [ ] Commit scripts to git (`data/` stays ignored).
- [ ] Add `docs/source_limitations.md` (provided) to the repo.
- [ ] Look at one product's edit history on the OFF website to see the data first-hand.
- [ ] Check raw data size on disk (`du -sh data/raw`) to plan storage and compression.
- [ ] Verify current API rate limit, Parquet export update frequency and schema, and ODbL attribution rules.
- [ ] Verify free-tier limits of any cloud tool before depending on it (Databricks, S3). Not verified so far.

## Phase 2 plan (to design next session)

1. Raw layout: one immutable file per (normalised barcode, revision), with checksum.
2. Ingestion manifest: source, request time, status, bytes, checksum, row or field counts, outcome per revision.
3. Idempotent, incremental fetcher: skip stored revisions; fetch only revisions newer than the stored maximum.
4. Barcode normalisation function with unit tests (8, 12, 13, 14 digit rules; zero padding).
5. Provenance extraction plan: editor per revision (`last_modified_by`, else set difference of `editors_tags` / `correctors_tags`), plus a documented account-category allowlist (individual, app, importer, bot, mass editor).
6. Ingest the contingency cohort as the first real workload.
7. First pytest tests (barcode normalisation, manifest idempotency), using the real cases listed in `docs/source_limitations.md` section 8.

## Scale notes

- Scaling beyond 44 products is possible but bounded by the API rate limit. At one request per 4.2 s, 1,000 products with about 20 revisions each is roughly 20,000 requests, about 23 hours of fetching in total (arithmetic from the stated limit; verify the limit).
- History is stored only for monitored products. Other products are covered by periodic catalogue snapshots; a rise in a product's `rev` between snapshots can promote it to the monitored list. Snapshot comparison at catalogue scale is the intended genuine Spark workload.

## Interview summary (current, honest version)

"I built a revision-aware pipeline on Open Food Facts that preserves product revisions, separates human edits from bot edits and system-recomputed fields, classifies record changes, and produces evidence-backed review candidates. Before building, I ran a feasibility study that showed most apparent changes are data completion or derived-field churn, so the design treats raw ingredient text as primary evidence and never claims a recipe changed."

## Handoff for a new chat

Paste this at the start: "Continue Ingredient Drift Radar. Read PROGRESS.md and source_limitations.md in project knowledge. We are starting Phase 2 (raw storage and ingestion manifest). Follow the working agreement in PROGRESS.md."