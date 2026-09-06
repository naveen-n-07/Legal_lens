# Legal Metrology (Packaged Commodities) Rules — Rule Engine Database

Built from the 39 PDFs (some duplicated) in `Legal_Metrology_Packaged_Commodities_Rules_2011.zip`.

## What's in here

| File | Rows | Purpose |
|---|---|---|
| `source_documents.csv` | 42 | Every PDF, catalogued with GSR number, gazette date, page count, and **extraction quality** (good/fair/poor) so you know how much to trust each one |
| `amendments.csv` | 21 | Every G.S.R. notification, with commencement dates and a `supersedes_amendment_id` chain |
| `legal_provisions.csv` | 47 | Hierarchical rule → sub-rule → clause text |
| `compliance_rules.csv` | 35 | Atomic, machine-executable checks (one field/condition each) |
| `product_categories.csv` | 19 | Applicability tags used to scope rules to commodity types |
| `rule_engine_rules.json` | 35 rules | Denormalized version of the above 5 tables, ready for your Python engine to `json.load()` directly — each rule carries its provision text and amendment lineage inline |
| `rule_engine.db` | — | SQLite with real foreign keys across all 5 tables (`PRAGMA foreign_key_check` passes clean) |

## How this was actually built (so you can trust it appropriately)

1. **Extracted text natively** (PyMuPDF) from every PDF that had a real text layer — mostly the 2021–2026 amendment notifications, which turned out to be clean bilingual (Hindi+English) gazette copies.
2. **OCR'd** (Tesseract, `eng+hin`) every scanned PDF with ≤6 pages — mostly DCA advisory circulars, several of which **quote exact rule text verbatim** (e.g. the medical-devices circular quotes Rule 3, Rule 26(c), and Rule 6(1)(e) word-for-word — that's a great, authoritative source).
3. **Sampled** (not fully OCR'd) the two huge files:
   - `6_...pdf` (655 pages) — turned out on inspection to be the **Legal Metrology (General) Rules, 2011** (weighbridge/tank calibration standards), **not** the Packaged Commodities Rules. Catalogued but out of scope.
   - `8 (1)_...pdf` (83 pages) — **is** the real 2011 principal notification, but is Hindi-only in this scan. Only pages 1 and 6–7 were OCR'd (confirming Rule 1 and the Rule 6 declaration text); the rest was **not** transcribed — see gaps below.

## ⚠️ Known gaps — do not treat these as ACTIVE without verification

- **Rules 8, 9, 11** exist in the principal Act but their exact current wording was **not** captured from these PDFs this session. They're in `legal_provisions.csv` as stub rows with `verification_status = NEEDS_SOURCE_VERIFICATION`. Get the principal 83-page PDF (`SRC-001`) OCR'd/translated properly (or pull the plain-text version from `consumeraffairs.gov.in`) before relying on them.
- **Table-I** (the letter-height-by-panel-area table under Rule 7(2)) was visible in the 2017 amendment OCR but not transcribed into structured numbers (`LM-CR-012` is `NEEDS_SOURCE_VERIFICATION`).
- Two amendments in the postponement chain (`AMD-2022-910`, `AMD-2023-463`) are referenced only in the "Note" of later notifications — the actual PDFs weren't in your zip. Dates are inferred from those notes.
- ~15 older (2011–2017) scanned amendments OCR'd to garbled text (bad embedded fonts / low scan quality). They're catalogued in `source_documents.csv` with `extraction_quality = poor` and `NEEDS_HUMAN_REVIEW` in their notes — re-scan at higher DPI or source clean copies if you need their content.
- Every row's `verification_status` field is there for exactly this purpose — **30 of 35 compliance rules are `VERIFIED_FROM_SOURCE`** (text traced to a specific PDF+page), the rest are `DRAFT`/`NEEDS_SOURCE_VERIFICATION` and should be reviewed by your team before the rule engine treats them as authoritative, per the DRAFT→VERIFIED→ACTIVE workflow you described.

## A genuinely useful finding baked into the data

The 2021 amendment (`AMD-2021-779`) had its commencement date postponed **nine separate times** (Apr 2022 → Oct 2022 → Dec 2022 → Jan 2023 → Feb 2023 → Apr 2023 → Jun 2023 → Jul 2023 → Sep 2023 → Oct 2023 → Jan 2024) before it actually took effect. This is modeled as a proper linked list via `supersedes_amendment_id`, and a recursive SQL query to walk it is in the test output. This is exactly the kind of temporal-versioning edge case your rule engine needs to handle correctly — worth a slide in your SIH demo.

## Quick start

```python
import json
rules = json.load(open("rule_engine_rules.json"))["rules"]
active_rules = [r for r in rules if r["verification_status"] == "VERIFIED_FROM_SOURCE"]
```

or query `rule_engine.db` directly with any SQLite client / `sqlite3` module — see the join examples used to sanity-check this build (recursive amendment chain, rule↔category joins, provision↔amendment↔source traceability).
