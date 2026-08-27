# Project goal

The standing execution and prioritization authority is
[`PROJECT_OPERATING_DIRECTIVE.md`](PROJECT_OPERATING_DIRECTIVE.md). Read and
apply it on every execution turn; it supersedes older queues when they conflict.

## One end state

Input: one or more scanned, born-digital, or mixed Vietnamese bank financial-report PDFs.

Output: a complete Excel workbook derived from the evolving `UNIVERSAL_BANK_BCTC_SCHEMA` and recording the correct value, period, unit, sign, statement, scope, section, and cell-level provenance for every accepted observation. The supplied 1,593-item template is the stable `BASE_SCHEMA`, not a closed universe.

The current statement scope is CDKT, KQKD, the applicable LCTT branch, and quantitative TM. CSTC is excluded unless the user changes scope.

## Current Gemini JSON-first architecture (binding)

The current production path is deliberately different from the legacy OCR
architecture. Gemini reads every PDF page first and returns versioned,
hierarchical JSON for financial statements and quantitative notes. PPOCR,
VietOCR, and geometry-derived reconstruction are not inputs to the production
mapping path. The source PDF remains the ultimate authority, but every graph,
accounting, arithmetic, schema-mapping, review, and export algorithm must query
the selected Gemini JSON evidence from the database instead of reparsing PDFs or
walking loose artifact files.

The database is the operational system of record. It must retain, at minimum:

- the immutable source/document/page identity and source hash;
- the raw model response and canonical parsed JSON;
- provider, model, prompt, response schema, token usage, cost, latency, attempt,
  and request/batch lineage;
- page, region, section, table, row, cell, header, hierarchy, period, unit, and
  value records with stable identifiers;
- all evidence versions, validation results, supersession links, and exactly one
  explicitly selected version for each production scope;
- family candidates, graph receipts, equations, mappings, dispositions, and
  export lineage.

Indexes, queries, caches, and physical data organization must be optimized so a
family run reads only the required document/page/region/row/cell records. Broad
database scans and full-PDF reconstruction are not acceptable in a normal
incremental run.

If OCR, a coordinate, a row, a cell, or a local hierarchy is wrong, the system
must re-extract only that bounded region, write a new immutable evidence version,
revalidate only its dependency closure, and atomically advance the selected
version. It must not rerun the whole file or accidentally combine records from
different evidence versions. Every cache key and derived receipt must include
the selected evidence-version dependency.

Family recognition is graph- and relation-first. A shared variant engine must
support legitimate changes in order, partial wording, optional/extra/missing
rows, headers, multilayer subtotals, parent/child, child/child, sibling,
neighbor, and continuation structure while recognizing the same accounting
family. Structure, local context, typed accounting relations, and exact
all-column equations take priority over literal name matching. Arithmetic may
validate a printed structure or support a uniquely constrained inference, but
must not silently repair source digits.

Every label must retain its exact source spelling and also receive shared
search forms: Unicode-normalized lowercase, accentless Vietnamese, collapsed
whitespace/line breaks, normalized punctuation, and bounded abbreviation
expansion. Declarative matchers may require an exact normalized alias, one
continuous core phrase, or multiple core phrases in declared order. A partial
phrase match is never standalone family authority: it must be corroborated by
the declared parent/child/sibling/neighbor context and the exact accounting
frontier. This permits stable meanings such as margin lending and securities
sale advances to survive organization qualifiers or wording changes without
accepting unrelated rows. Exact source text and the matcher policy used remain
in the evidence receipt; normalized text must also be indexed in the database.

Families that share a structural mechanism must use the same engine and
primitive with declarative family-specific roles, aliases, variants, and
equations. Do not create a separate algorithm file per family unless a genuinely
new reusable mechanism has first been demonstrated. Production must map an
unseen filing automatically from configuration and selected database evidence;
per-bank, per-page, per-document, and per-family repair routing is not an
acceptable operating model.

Every run must emit stage timings, query counts, rows/bytes read, cache hit rates,
model/token/cost totals, retry counts, and invalidation scope. The system must
continually identify its current bottleneck and improve the shared architecture.
The scalability target is more banks, periods, statement types, and families
without starting over or recomputing unaffected evidence.

## Definition of done

A production run is complete only when all of the following are evidenced:

1. Inputs, code, config, model, and outputs have stable hashes and a run manifest.
2. Source PDFs remain unchanged and are the final authority.
3. Gemini page extraction is reproducible from immutable raw responses,
   canonical JSON, prompt/schema/model identity, and database checkpoints.
4. Period, unit, sign, scope, row, column, and schema binding are independently represented.
5. Every exported value has document/page/region/table/row/cell evidence lineage
   back to the selected Gemini response and source image. Coordinates may be
   retained as optional evidence but are not mapping authority.
6. Blank, zero, dash, not applicable, and not observed remain distinct.
7. Uncertain or conflicting results fail closed to review or unresolved.
8. Role A machine reference and Role B production are isolated during frozen evaluation.
9. Applicable coverage and full-tuple accuracy are measured per statement and TM group against an explicit denominator.
10. The output workbook preserves every accepted ReportNormId and accounting meaning, uses explicit universal `DisplayOrder`/`ParentId`, represents evidence-backed additions, and includes PROVENANCE, REVIEW, UNRESOLVED, QUESTIONS, SCHEMA_ADDITIONS, and RUN_METADATA.
11. A versioned off-machine backup, MongoDB dump where applicable, and restore test all pass.
12. Family graph and equation evaluation reads the selected JSON evidence through
    indexed database queries; the run manifest proves bounded reads and stable
    cache/version keys.
13. A bounded evidence defect can be repaired and replayed without rerunning its
    whole PDF, and stale or cross-version derived data is rejected.
14. The same shared graph primitives pass order/name/optional-row/subtotal/header/
    hierarchy/neighbor/continuation variants and fail closed on ambiguous,
    partial, mixed-level, duplicate-use, period, unit, or arithmetic conflicts.
15. A clean unattended production pass can process families from Family 1 to the
    final family across all banks without source-code edits for individual
    families, banks, documents, pages, or values.

## Non-goals

- Reconstructing the lost implementation line by line.
- Treating the database, an OCR model, a VLM, or an accounting equation as truth
  independently of its selected, versioned source evidence.
- Maximizing raw mappings at the cost of accuracy or traceability.
- Tuning on an untouched holdout.
