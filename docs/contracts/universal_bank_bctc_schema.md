# Universal Vietnamese-bank BCTC schema contract

## Purpose

The schema serves the PDF-to-financial-data pipeline. It is not a closed list that a source PDF must be forced to fit.

`BASE_SCHEMA` is the original supplied 1,593-item reference. Its accepted ReportNormIds and accounting meanings are immutable inputs to schema evolution.

`UNIVERSAL_BANK_BCTC_SCHEMA` is the current base plus append-only identities supported by real Vietnamese-bank financial-statement evidence. It covers CDKT, KQKD, direct and indirect LCTT, and quantitative TM across banks, periods, and consolidated/separate scopes.

The universal schema is a superset. A bank is not expected to report every universal item.

## Source-driven decision flow

For every legitimate visible accounting row:

```text
PDF label, values, hierarchy, neighbors, statement, section and axes
  -> search the current universal schema
  -> equivalent accounting identity exists?
       YES: reuse its ReportNormId and retain the visible wording as evidence/alias
       NO: genuine distinct accounting concept?
            YES: add an audited stable identity
            UNCLEAR: retain AMBIGUOUS/UNRESOLVED and ask only the necessary question
```

A row must never be force-mapped merely because the base schema lacks an exact item. It must not disappear as permanent source-only data when evidence establishes a real schema gap.

Measure axes, percentages, geographies, class columns, duplicate totals, and validation-only calculations remain first-class provenance when they are not separate accounting-row identities. They do not require artificial ReportNormIds.

## Identity, hierarchy, and order

`ReportNormId` is a stable identity only. Its numeric magnitude has no presentation semantics.

Every accepted item retains at least:

- ReportNormId;
- canonical name;
- statement and section;
- ParentId;
- hierarchy level;
- DisplayOrder;
- row role such as heading, parent total, subtotal, or detail;
- schema origin/evolution batch;
- source evidence.

New identities use unused append-only IDs. They are inserted into the correct accounting position through `DisplayOrder` and parent/child links, even when their numeric IDs are much larger than adjacent items.

A visible subtotal that owns visible details is represented as their parent. A presentation column or measure must not be flattened into a false row hierarchy.

## Alias versus new concept

Reuse one canonical identity when differences are limited to OCR noise, punctuation, capitalization, abbreviations, singular/plural wording, minor regulatory wording, or bank-specific phrasing with the same accounting meaning and hierarchy.

Create a new identity only when statement, section, parent/children, row role, accounting meaning, or measure is materially different. Label similarity alone cannot decide equivalence.

Each accepted alias retains its text, normalized retrieval key, kind, source evidence, and authority. A former canonical name remains an alias after an evidence-backed display-name correction. Alias retrieval must fail closed when one normalized alias would silently select different accounting identities.

## Observation and absence states

Cell and schema states remain distinct:

```text
OBSERVED_VALUE
OBSERVED_ZERO
DASH
BLANK
NOT_OBSERVED
NOT_APPLICABLE
AMBIGUOUS
UNRESOLVED
```

`DASH` and `BLANK` have no numeric value and are never coerced to zero. `NOT_OBSERVED` means the universal item is absent from the document or explicitly scoped statement pages; it does not imply extraction failure. `NOT_APPLICABLE` is used only when the item or branch does not apply to that document.

## Evolution audit

Ordinary schema growth uses one reusable migration path, not a new E-series experiment. Each evolution batch must:

1. verify the exact base/current input hashes;
2. preserve every existing ID and accounting meaning;
3. record before/after universal-schema hashes and the new high-water mark;
4. allocate globally unique IDs;
5. record canonical name, statement, section, parent, level, final display order and neighbor anchors;
6. record source bank, document hash, page, source row/label, values or statuses, and why existing items are insufficient;
7. record aliases and any evidence-backed parent correction;
8. replay deterministically and validate hierarchy, cycles, formulas, registry, coverage, and exporter contracts.

Accepted IDs are not deleted, reused, or semantically changed without explicit migration logic and evidence.

## Role A and Role B

Role A independently preserves every genuine visible accounting row. It may flag `POSSIBLE_SCHEMA_GAP`; it is not restricted to populating the current schema.

Role B independently discovers or maps the same concept using only its allowed production evidence. Role A answers, historical MongoDB data, human-review registries, and holdout artifacts cannot become mapping hints.

Both roles emit exact source dispositions so schema coverage cannot hide dropped source rows.

## Coverage reporting

Every milestone reports two denominators.

Universal coverage reports item counts for CDKT, KQKD, LCTT, and TM, the universal revision/hash, and the base-versus-added identity count.

Per-document coverage reports:

- legitimate visible source rows/cells;
- rows reused against existing canonical IDs;
- newly discovered schema identities;
- aliases resolved;
- ambiguous and unresolved rows;
- validation/measure/context-only rows;
- source rows successfully accounted for over total visible rows;
- universal items mapped, not observed, not applicable, ambiguous, and unresolved for that document.

A growing universal denominator must not reduce a document's measured extraction quality merely because other banks report additional items.

## Excel and provenance

Every accepted universal item is present in the supplied-template-derived Excel contract. Observations retain exact value status, period, unit, scope, source row/cell, evidence hashes, mapping basis, and validation results. Newly added identities participate in the same deterministic export, no-overwrite, provenance, and recovery contracts as base identities.

Schema evolution remains subordinate to the final product:

```text
PDF -> statements -> rows/cells -> OCR -> accounting structure
    -> reuse identity or add evidenced identity -> validate -> Excel
```
