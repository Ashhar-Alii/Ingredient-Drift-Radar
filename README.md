# Ingredient Drift Radar

A revision-aware data pipeline on [Open Food Facts](https://openfoodfacts.org) (OFF)
that preserves product revisions, separates human edits from bot edits and
system-recomputed fields, classifies record changes, and surfaces
evidence-backed candidates for human review.

> **Important:** OFF is community-edited. This project detects *changed
> records*, not proven recipe changes. Alerts never claim a product,
> recipe or formulation changed, and make no food-safety claims.
> See [docs/source_limitations.md](docs/source_limitations.md).

## Status

Phase 2 of 10 in progress: raw storage, ingestion manifest and an
idempotent, rate-limited revision fetcher.

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Data validation (44 products, 814 revision pairs) | Done |
| 2 | Raw storage, manifest, idempotent fetcher | In progress |
| 3-10 | Spark, Delta Lake, dbt, Airflow, CI/CD, dashboard | Planned |

## What Phase 1 found

- Most apparent "changes" are data completion or system-derived tag churn,
  not edits to ingredient content (52 of 62 tag changes had identical
  ingredient text).
- Revisions mix human-edited fields with fields OFF recomputes, and some
  are saved by bots or importers.
- Barcodes can change format between revisions (e.g. `071109` to `00071109`).

These are measurements from a small, deliberately biased 44-product
cohort, not database-wide rates.

## Design principles

- Immutable raw layer: store API responses untouched; rebuild everything else.
- Idempotent ingestion keyed on (normalised barcode, revision).
- Primary evidence is raw ingredient text and user-entered allergen
  fields; derived tags are context only.
- Preserve and flag bad data; never silently drop it.

## Planned stack

Python ingestion, DuckDB, Apache Spark, Delta Lake, dbt, Airflow,
GitHub Actions. Free tools only, developed on a 12 GB RAM laptop.
Components are added phase by phase; only Python and DuckDB are in use today.

## Repository layout

- `ingestion/`: API probing, cohort selection, revision fetching, analysis
- `src/ingredient_drift/`: reusable, tested logic (barcode normalisation, ...)
- `tests/`: pytest unit tests
- `docs/`: source limitations and design decisions

## Data and licence

Data comes from Open Food Facts, published under the Open Database
License (ODbL); individual contents may carry separate terms. Raw data is
not committed to this repository. Attribution requirements for any
published derived dataset are still to be reviewed.

## Setup and Installation

### Prerequisites
Ensure you have Python 3.10+ installed.

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd "Ingredient_Drift_Radar"
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   
   # On macOS/Linux:
   source .venv/bin/activate
   # On Windows:
   .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration:**
   Copy the example environment template to create your local configurations:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill out your actual contact details. Open Food Facts requires a non-generic `OFF_USER_AGENT` value containing a valid email address so they can contact consumers of their free API if issues arise.

## Running the tests

Ensure your virtual environment is active, then execute:

```bash
pytest
```
