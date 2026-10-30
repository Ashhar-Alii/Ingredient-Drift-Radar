# Source Limitations and Phase 1 Findings

Project: Ingredient Drift Radar
Status: Phase 1 (data validation) complete. Written 2026-10-31.
Scope of evidence: 44 products, 814 consecutive revision pairs. This is a small, deliberately biased feasibility cohort, not a statistical sample of Open Food Facts.

## 1. What this document is for

This file states what the source data can and cannot support, using what we actually observed. Every claim the pipeline, alerts, README or interviews make must stay inside these limits. Numbers below are measurements from our own runs, not properties of the whole database.

## 2. The source

Open Food Facts (OFF) is a community-edited, crowdsourced food product database.

- Contributors are volunteers, mobile apps, producer integrations, importers and automated bots.
- OFF's own terms state that the information is indicative and that accuracy and completeness are not guaranteed.
- The database is published under the Open Database License (ODbL). Individual contents can carry separate terms. Review attribution and reuse requirements before publishing any derived dataset or app.
- Product data comes from two resources with different properties:
  - The current catalogue (bulk Parquet export): millions of rows, current state only.
  - Per-product historical revisions: retrieved one request at a time through the API using the `rev` parameter.

## 3. What the data can prove

- That the stored record for a barcode differed between revision A and revision B.
- Which fields differed, when the revisions were saved, and (where recorded) which account saved them.

## 4. What the data cannot prove

- That a manufacturer changed a recipe.
- That a product is safe or unsafe.
- That an allergen was added to or removed from a physical product.

A changed record is evidence of an edit to the database, not of a change to the food.

## 5. Phase 1 measurements

| Measure | Result |
|---|---|
| Products in feasibility cohort | 44 |
| Products with at least 2 honoured revisions | 44 / 44 |
| Products with ingredient text in at least 2 revisions (first sampled run) | 41 / 44 |
| Revision requests missing (first sampled run) | 0% |
| Consecutive revision pairs analysed | 814 (2 pairs spanned a gap of more than 1 revision) |
| Ingredient text: both_missing / no_change / completion / set_change / formatting_only | 456 / 299 / 43 / 11 / 5 |
| Allergen tags: same / from_empty / added / removed / not_comparable | 656 / 29 / 6 / 3 / 120 |
| from_empty allergen changes that coincide with a data-completion event | 25 of 29 |
| Products with at least one material candidate, text comparison | 12 / 44 |
| Tag changes between revisions (canonical `en:` tags) | 62 pairs, in 30 / 44 products |
| Tag changes where ingredient text was identical | 52 of 62 |

Manual review of the 12 text-based candidates found mostly punctuation or segmentation artefacts of our own crude normalisation, OCR typo fixes, pack text or multilingual text pasted into the ingredient field, and bot re-saves. Roughly one case looked like a human edit that changed the listed ingredients (a sweetener list rewritten by a volunteer). That case is still not evidence of a recipe change.

## 6. Limitations

### L1. Community-edited data
Edits include corrections, completions, translations and cleanups. Most observed "changes" were not new information about the product.
Pipeline response: classify every change; alerts say "record changed", never "recipe changed".

### L2. No bulk history
OFF does not publish a bulk dump of all historical versions of all products. History exists per product through the API, under a documented rate limit (the blueprint cites 15 product reads per minute per IP; verify the current limit) and a requirement for an identifiable User-Agent.
Consequence: historical analysis covers a monitored subset, not the whole catalogue.
Pipeline response: queued, rate-limited, cached ingestion; full catalogue used for current-state processing and for detecting which products changed.

### L3. Cohort bias
The cohort was a seeded, stratified selection from a catalogue snapshot (up to 8 products per stratum, deduplicated), restricted to products with 8 to 40 revisions and non-trivial ingredient text. It is not a random sample.
Consequence: rates observed here (for example, share of products with a candidate change) must not be quoted as database-wide rates.
Pipeline response: record cohort selection rules; expand through a second cohort (higher revision range) and report results per cohort.

### L4. Early revisions are mostly empty
56% of pairs had no ingredient text on either side. Products are typically created with a barcode and name, then completed.
Consequence: the most common "change" is a data-completion event (43 pairs), not a modification.
Pipeline response: a distinct data-completion class that is excluded from material-change alerts and reported separately.

### L5. A revision bundles human edits with system recomputation
Each revision snapshot contains human-edited source fields and many system-derived fields (tags, hierarchies, analysis flags, Nutri-Score data, data-quality tags, popularity tags). OFF recomputes derived fields using its parser and taxonomies at the time of a save. 52 of 62 tag changes occurred with identical ingredient text.
Consequence: comparing derived fields produces false change signals.
Pipeline response: treat source fields (ingredient text, user-entered allergens and traces, labels) as primary evidence; treat derived fields as context only. Add an explicit "derived-data churn" class.

### L6. Editors are not all individual volunteers
Observed accounts include importers, apps and bots (for example `fix-code-bot`, `tacite-mass-editor`, `openfood-ch-import`). One observed revision (barcode padding fix) was saved by a bot and also recomputed allergen fields while the ingredient text was unchanged.
Consequence: an allergen or tag change can be a bot re-save, not a contributor declaration.
Pipeline response: attach an editor provenance category to each revision. Newer snapshots expose `last_modified_by`; older ones require inferring the editor from new entries in `editors_tags` / `correctors_tags` (ordering of those lists is not stable, so use set differences). The mapping from account name to category (individual, app, importer, bot or mass editor) is a heuristic allowlist that we maintain and must verify.

### L7. Edits can be seconds apart
One observed pair of revisions was saved 7 seconds apart by the same contributor session.
Consequence: one logical correction can appear as several revisions.
Pipeline response (Phase 4 design decision): coalesce nearby revisions by the same editor into an edit session before classifying a change.

### L8. Ingredient text can be polluted
Observed contamination: OCR errors, several languages in one field, nutrition tables, storage advice and allergy advice pasted into the ingredient text. Splitting on commas and comparing sets then reports huge differences.
Consequence: text-set comparison can be wrong in both directions.
Pipeline response: data-quality classification for polluted or ambiguous text ("incomplete or ambiguous"); keep original text with every alert; test normalisation against the real cases listed in section 8.

### L9. Empty allergens are ambiguous
An empty allergen list can mean "no allergens declared" or "not filled in yet". The allergen tag field was absent in 120 of 814 pairs because older revisions lack it. Allergen tags combine user-entered and ingredient-derived parts in newer revisions.
Pipeline response: keep absent, empty and populated as separate states; separate user-entered allergen fields from ingredient-derived ones where the snapshot provides both; never treat from_empty as a newly declared allergen without a completion check.

### L10. Identifier instability
Barcode formatting changed between revisions (a 6-digit code became an 8-digit zero-padded code). Folder and file keys must therefore use a normalised barcode.
Pipeline response: a tested barcode normalisation function (padding rules for 8, 12, 13 and 14-digit codes) and a key of (normalised barcode, revision number). Treat changes of identifier as a possible new entry and flag it.

### L11. Schema and type drift across years
Older revision snapshots lack fields present in newer ones, and some fields change type (for example `nova_group` as string in one revision and integer in another).
Pipeline response: a data contract for accepted fields, explicit type casting in the Silver layer, and a schema-evolution test.

### L12. Reconstruction of history is sampled in the first run
The first fetch sampled about 10 revisions per product; the final analysis used all consecutive revisions for products with up to 40 revisions. Products whose live revision count exceeded the cap were sampled, which explains the 2 pairs with a gap larger than 1.
Pipeline response: the fetcher records which revisions were requested and the outcome of each.

### L13. Manual review is not ground truth
Review labels came from truncated strings and one reviewer's judgement. They are working labels.
Pipeline response: keep reviewed pairs as labelled test fixtures; extend them as more cases are reviewed.

### L14. Snapshot versus live API
The catalogue snapshot and the live API can disagree on a product's current revision. Snapshot schema and update frequency must be checked each time (not verified here).

## 7. Rules for alert wording

Allowed:
- "The record for barcode X changed between revision A and revision B."
- "The ingredient text differs. Evidence: previous text, new text."
- "Saved by account Y (category: individual / app / importer / bot)."
- "Classification: data completion / formatting only / ingredient list change / allergen field change / derived-data change / ambiguous."

Not allowed:
- Any claim that the recipe, formulation or product changed.
- Any food-safety or health conclusion.
- Any accusation about a manufacturer.

## 8. Real cases kept as test fixtures

1. Bracket style change only: `[...]` versus `(...)`.
2. A comma added between two items.
3. OCR typo corrected, with allergen tag derived from the corrected word.
4. Several languages in one ingredient field.
5. Nutrition table or pack advice text inside the ingredient field.
6. Non-English-language tags appearing among allergen tags.
7. Empty allergen field becoming populated alongside a data-completion event.
8. Bot re-save that changes derived allergen fields while ingredient text is unchanged.
9. Barcode zero-padding change between revisions.
10. Two revisions seconds apart from one editor session.

## 9. Open questions to verify

- Current API rate limit and any usage terms for the revision parameter.
- Update frequency and schema of the bulk Parquet export.
- Which account names should count as bots, importers or apps (maintain a documented list).
- Whether parsed ingredient `text` values are stable across revisions (ids are not).
- Attribution requirements for publishing results.

## 10. Change log

- 2026-10-31: Initial version from Phase 1 findings.