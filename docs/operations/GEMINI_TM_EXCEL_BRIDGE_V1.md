# Read-only Gemini canonical-store to TM Excel bridge V1

Implementation checkpoint: **synthetic gate PASS; no real-store/financial
acceptance**. Root ran the reviewed implementation at
`a050d1ce5940ee7b4cdf5cdcb2792db0071ddee0` in a fresh clean Linux clone:
Ruff PASS and 85 tests PASS in 46.62 seconds, Python 3.12.3, 2 GiB address-space
cap, nice 19, under the serialized test lease. Real restored-store, corpus,
PDF and provider jobs remain coordinator-owned. Authoring itself used native
source text only; the tests use owned synthetic source/store/PDF bytes.

Branch `codex/tm-excel-bridge-v1` starts at exact migration base
`8efd618b6c77f0cdbb402a440e7ba3b3549184f1`. The isolated native clone was made
from the previously verified local Git object database with `--no-local` and no
alternates after GitHub DNS failed. The coordinator subsequently reverified the
live integration branch at the same base. No push is authorized until review
and tests pass. All five mandatory migration/operating documents were read
before product code was written. Frozen evaluator, runner, schema and template
bytes are unchanged.

## Implemented path and boundary

`export_tm_multitable_store_document_v1(*, request: dict) -> dict` in
`bctc_ai.export.gemini_tm_multitable_bridge_v1` authenticates a sealed SQLite
snapshot and one exact persisted family run, including every persisted trial,
candidate and mapping row. It checks store/run IDs, metrics, canonical byte
hashes, specs, requested execution kind and optional current selection. It
requires the caller's pinned implementation axis to equal the stored run axis,
hashes its actual files and binds the loaded evaluator/store/replay callable
origins to those files. A caller-supplied Git HEAD is not accepted as proof.

It then invokes the base store's existing authenticated selected-corpus frontier
and existing MULTITABLE source replay read-only over the complete stored trial
axis. It does not ingest, select, repair or create a database. The wrapper uses
SQLite `mode=ro&immutable=1`, query-only, quick_check and foreign_key_check;
sidecars cause a stop. Existing page-store APIs may create connection-local TEMP
tables while keeping the main database read-only. Corpus manifests, selected
page lineage, source DB hash, global document ordinal, exact source PDF
hash/size/path and selected source locators are bound before projection. The
existing authenticated-frontier helper is a private base API, intentionally
named and pinned here; a future incompatible base requires review, not a
dynamic API fallback.

Both public entry points snapshot the request through strict canonical JSON
before reading policy controls; callbacks cannot relabel checked run-kind,
selection policy or output roots by mutating the caller's dictionary. Both
SQLite inputs are checked for new `-wal`, `-shm` and `-journal` sidecars after
source loading and again after workbook readback/final byte checks, before
publication. A writer must remain excluded for the life of the sealed snapshot;
these barriers do not claim to lock an unrelated writer process atomically.

The implementation axis authenticates the producer files recorded in the run
and the loaded callable origins named above. It is not an independent hash pin
of every transitive Python/helper/environment dependency. A fresh, clean pinned
project environment is required. A broader consumer/dependency manifest remains
a separate proposed extension; no full Python dependency-closure claim is made.

Proposed extension, not implemented or an acceptance gate in V1: retain the
historical stored producer axis unchanged, and link a separate reviewed
`consumer_manifest` by canonical JSON digest. Its explicit authority would bind
the bridge, renderer, canonical XLSX helper, observation/contract helpers and
every actually used transitive project module by repository-relative path,
SHA/bytes and loaded origin; it would also bind Python 3.12 patch version and
the approved OpenPyXL/dependency distribution artifacts. The reviewed manifest
must declare the dependency frontier in advance. Runtime discovery is only a
check against that frontier, never authority to approve newly discovered code.
Fresh import/cache provenance and any producer-to-consumer compatibility review
would be separate fields. Missing/drifted/extra used dependencies would stop;
historical producer refs would not be rewritten to current consumer bytes.

`project_multitable_document_v1(bundle) -> list[dict]` converts **all** mapping
lanes in the requested READY document or stops the entire document. Initial
support is deliberately a source grammar subset of codec
`GEMINI_JSON_MULTITABLE_HIERARCHICAL_ACCOUNTING_FAMILY_V1`:

- Direct or corroborated rows whose cells are exactly `RAW_SIGNED_INTEGER`,
  `DASH_ZERO` or `BLANK_SOURCE_CELL`, with the same exact source cell text,
  integer coefficient, sign and state as the selected JSON.
- Ordinary one-to-one ordered source money columns. Every contributing source
  row must join to one exact table receipt; every full period must agree across
  corroborating rows; the unit must be complete and equal to that table's
  authenticated canonical unit.
- SNAPSHOT lanes with a complete source `DATE` become `STOCK_AS_OF`; DURATION
  lanes with `DURATION_DATE_RANGE` become a complete `FLOW_RANGE`. The source's
  newest distinct dated lane is CURRENT, and an existing semantic role must
  agree. Current reporting dates must agree across the document, be from 2025
  onward and not exceed the execution date. Comparative 2024 columns within a
  qualifying report are retained. No filename is used to determine a period.

The static inventory counts 25 families configured for this codec. **This is
not a claim that 25 real stores/documents have been exported.** Initial source
grammar support and actual export coverage are different denominators.

Derived sums, role unit overrides that do not match a source-table unit,
transposed/split column projections, repaired punctuation states, ratio codecs,
semantic-only/bare-year/end-date-only flow periods, unknown states and other
codecs stop explicitly. There is no fallback, skipped mapping or partial
document success. Non-READY documents also stop instead of producing an empty
workbook that could be mistaken for an accepted report. Their unchanged source
dispositions remain in the canonical store.

The whole stored sweep is scanned for legacy state names containing
`BLANK_ZERO`, `ONE_UNKNOWN`, `BACKSOLV` or `IMPUT`, including nonselected
candidates. These remain prohibited even when a historical run is OFFICIAL.
The current source-observation contract is validated independently.

## Workbook and receipt

`bctc_ai.export.gemini_projected_tm_workbook_v1` adapts the reviewed 0401
projected-renderer approach to migration-base `canonical_xlsx.py` and OpenPyXL;
it imports neither missing `notes.export_v1` nor PRIMARY exporter modules.

The input template is fixed to `template/Bank_TM_ReportNormId.v2.xlsx`, SHA-256
`64589f7ee2b025ac0bd784c13e0b0ba0aff9d46456a83fa7fe2d68a7de375115`.
Its existing RNID/name axis in columns B/C is read in order and reproduced in a
new TM sheet. The template itself is never modified; this renderer reproduces
the schema axis, not the original template's formatting or column layout.
One document/RNID/full-period slot may have only one record, including when
duplicates have equal values. Unmapped template slots are explicitly marked
`NO_ACCEPTED_MAPPING_FOR_SLOT`, never zero.

Numeric zero remains numeric zero. A printed dash remains its exact literal
string with `DASH_ZERO`; a blank remains None with `BLANK_SOURCE_CELL`. All
integers over 15 decimal digits are exact decimal **text** with an explicit
number-policy field; shorter integers are numeric. This avoids Excel precision
loss without pretending that a rounded floating-point number is exact. No
scale conversion, sign flip, imputation or equation backsolve is performed.

The original trial (including source-only observations and closure receipts),
source locators, complete period/unit evidence, implementation refs, source
PDF identity, SQLite run/sweep identity, schema binding and template ref are
retained in canonical JSON provenance chunks. Each chunk is at most 12,000
Unicode characters (24,000 UTF-16 units), with its full JSON digest and chunk
axis. Formula-like source text is always literal. Excel row/column limits fail
closed. Per-document projection/provenance is bounded to 32 MiB each; the
existing whole-sweep loader is bounded to 256 MiB, **not streaming**. Existing
full source replay also hydrates selected pages; no throughput benchmark is
claimed. A future streaming/authenticated replay cache needs separate review.

Serialized XLSX bytes are reopened and compared against every expected cell's
exact value **and type**, full sheet axis and value-bearing cell dimensions.
Empty styled XML cells beyond the semantic grid are not an additional promise.
There must be no formula. All pinned bytes are reauthenticated after replay and
readback. Only then is the new absolute external output directory created
exclusively. Git worktrees, symlinks/junctions and input authority roots are
forbidden output locations. Existing output directories are never reused.
An I/O failure may leave a partial new directory; it is a failed export and is
not deleted or overwritten automatically.

Outputs are `tm.xlsx`, linked `receipt.json`, and `receipt.sha256`. The receipt
binds actual XLSX bytes, projection digest, full upstream provenance and exporter
implementation bytes. `receipt_material_sha256` hashes the canonical receipt
before adding that field; `receipt.sha256` hashes the complete receipt file,
avoiding an impossible literal self-hash. Output bytes are deterministic for
unchanged inputs; the receipt additionally records the scope-check date and
output path. Every output is labelled
`EXPERIMENTAL_READONLY_TM_EXPORT_NOT_FAMILY_ACCEPTANCE`.

This module does not certify family PDF residual/visual coverage, seal a family,
promote a selection, edit S3 or claim F36/F37/F39 closure. F36 COMPACT_A remains
EXPERIMENTAL and retains its existing OFFICIAL fence. The F37 dedicated exporter
on Claude's branch is not imported or superseded. Newer family-local producers
or repairs that cannot replay under the pinned base are unsupported. F41 stays
locked under the existing coordinator gates.

## Coordinator execution entry point

Only the coordinator may run synthetic tests. Actual restored-store, source
PDF and export jobs remain Claude's lease. The following is a product entry
point, **not an instruction to start a job now**:

```text
PYTHONPATH=src python3.12 -X pycache_prefix=<fresh-external-cache> scripts/export_gemini_tm_multitable_workbook_v1.py --request <absolute-owner-reviewed-request.json> --request-sha256 <actual-64-hex> --request-size-bytes <actual-byte-count>
```

The UTF-8 request has exactly these keys; refs contain exactly `path`, `sha256`
and positive integer `size_bytes`. All reference paths are absolute. Pin values
must come from the reviewed store/receipt authority; do not infer a run ID or
reuse an earlier-code receipt:

```text
store_ref, family_run_id, corpus_index_ref, source_page_database_ref,
corpus_artifact_root, effective_page_artifact_root (absolute path or null),
source_pdf_root, producer_root, producer_refs (the exact stored ordered axis),
document_ordinal (global integer), expected_family_id,
expected_run_kind (EXPERIMENTAL or OFFICIAL), require_current_selection (boolean),
template_ref, output_dir (new external absolute directory).
```

Existing producer refs relative to the producer repository are resolved against
`producer_root`; absolute producer refs retain their exact path. Runtime callable
origins must match the resulting actual files. No namespace remapping or fake
import substitution is performed. Metadata duplicate keys/nonfinite tokens are
rejected. Output receipts are separate linked XLSX receipts, not insertions into
the existing JSON-only `family_export` table.

## Verified synthetic controls

`tests/unit/test_gemini_tm_multitable_bridge_v1.py` covers direct source joins,
global ordinals, exact stock/flow periods, absent/full period distinctions,
role/RNID/unit/sign/source locator tampering, semantic-role conflicts, unknown
and derived states, blank/dash/zero distinctions, large positive/negative integer
readback, formula-like literal text, deterministic XLSX bytes, source-only
provenance, duplicate equal-value slots, boolean-vs-zero readback, historical
imputation rejection, 2024-report exclusion with 2024-comparative retention,
non-READY rejection, strict JSON, actual callable origins, readonly synthetic
SQLite, source-file pins, sidecars and untruncated provenance chunks.

The added real synthetic end-to-end fixture uses the existing base F40 configs,
source-page store, document-manifest/index builders, indexed region query,
candidate evaluation, persisted OFFICIAL store ingest, full source replay and
the real pinned TM template asset. It calls the bridge authenticator and exporter
without mocks of admission/validators. Its PDF bytes are a 123-byte synthetic
identity fixture, never rendered; provider observations use the existing inert
unit fixture, never a network call. Additional fault-injection controls create
new SQLite sidecars after callbacks and mutate the external request dictionary.

Root executed the two new bridge/publication modules plus existing
`tests/unit/test_canonical_xlsx.py`: all 85 tests passed. The complete run
receipt, source hashes, actual import origins, resource limits and JUnit are
retained under
`D:\bctc_bank\restore-receipts\CODEX_TM_EXCEL_BRIDGE_TESTS_20261026_V1\tm-excel-tests-20261026-v1\`.
Receipt SHA-256:
`27954694fa51cdef73935200b9da85e8b769093ca8ea3cfbd2eb6c6d6c1a1e0a`.
This includes the real synthetic store/source E2E with unmocked authentication
and validation, all six post-render DB-sidecar controls, request snapshots and
the explicitly labelled publication-wiring/readback fault controls.

Independent static review of the source/final delta found no material finding
in its stated scope. Its external receipt
`CODEX_TM_EXCEL_BRIDGE_STATIC_REVIEW_20261026_V1.json` has SHA-256
`c5fa97eb8415400e9c33d1fe8e5bc7e57726a005a5226120a5b06677e60e4d83`.
That receipt is source review, not a second execution claim.

The initial bridge still needs a separately owned real-store proof. No real
export coverage, corpus-scale memory/performance result, complete transitive
consumer-source attestation or financial acceptance is asserted. The approved
consumer-manifest and efficient authenticated-run/session designs need separate
implementation/review; the current entry point repeats full-run authentication
for each requested document. Existing frozen/template files remain unchanged.
