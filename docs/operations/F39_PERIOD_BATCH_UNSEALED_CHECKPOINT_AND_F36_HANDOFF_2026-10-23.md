# F39 period batch: unsealed checkpoint, then F36

Status: **DEVELOPMENT CHECKPOINT — F39 NOT TERMINAL**.
Scope remains bank reports from 2025 to current. Standalone 2024 reports are
outside production/provider queues; printed comparative 2024 columns remain
source evidence in in-scope reports. No provider calls or legacy OCR were used.

## Binding user workflow amendment

On 2026-10-23 the user directly answered the root-thread question with:
"Cho phép chuyển F36 sau checkpoint F39".

After recording and pushing this unsealed F39 checkpoint, the laptop integrator
may proceed to F36 OPERATING_EXPENSE without first declaring F39 terminal.
This supersedes only the earlier F39-terminal-before-F36 sequencing restriction.
It does not waive any acceptance, source/PDF, replay, observation, SQLite,
residual, tamper or ledger gate. F37 follows; do not open F41 before F39/F36/F37
are terminal and the required checkpoint is backed up. Do not label algorithm
holds as genuine issuer conflicts merely to close a family.

Use task-owned branches. This checkpoint belongs on
`codex/f39-income-tax-laptop`, descending from
`645827de94ae475a7aae6699e158969c4dc6558c` and migration base
`8efd618b6c77f0cdbb402a440e7ba3b3549184f1`. Do not push directly to
`codex/27-bank-2025-current`. Claim F36 through immutable coordination events
before its production mutation; review and focused-test worker changes before
promoted cherry-picks.

## Implemented F39 changes

Exactly five existing functions changed in the family-local evaluator:

- `_owned_flow_date_range_caption_constraint`: whole bare primary-income
  captions with explicit slash/written interim date ranges; preserve legacy
  receipts and reject unsupported annual/prologue/extra-assertion variants.
- `_owned_flow_report_quarter_constraint`: whole primary-income quarter-ended
  caption, literal ASCII tokens and valid calendar quarter endpoint. This is
  endpoint evidence, not an invented start/comparative window or scope/unit.
- `_printed_ytd_sibling_period_evidence`: finite shared current-frame and named
  quarter YTD headers, matching all four columns and explicit year rules.
- `_owned_current_period_constraints`: exact uniquely owned single-table
  primary-income first-3/6/9/12-calendar-month narrative, preserving raw text.
- `_owned_current_period_constraints_match`: enforce its full month length,
  not just coincident ending date.

All other production ASTs were checked unchanged. Evaluator SHA-256:
`776770e7cb2b5485fb12b44b6f408b0914221a7686bb07375006b26c440bb6c8`.
No F36/F37 or frozen shared code was modified by this checkpoint.
Four regression modules accompany the changes. The range tests call actual
production helpers, not the prototype relevance/canonical stubs; seven legacy
receipt hashes were captured before activation from evaluator `17752158…`.

## Focused evidence, including retained failures

All paths below are local immutable evidence under `/srv/bctc-receipts/`.
Coverage is composed with exact node/source-byte checks, not by relabeling a
failed execution or counting skipped/unexecuted nodes as passed.

| Evidence | Result | SHA-256 |
| --- | --- | --- |
| `f39-period-batch-focused-20261023T065200Z/F39_PERIOD_BATCH_FOCUSED_RECEIPT_V1.json` | Retained FAIL: 808 normal passes, one test-only NameError, 22 subtest passes; all original 688 plus 118 new function tests passed | `7fa3db383a7682f60998b4978e2da57a8023b4a520fb083a164767f6af972fad` |
| `f39-period-remaining-focused-20261023T072200Z/F39_PERIOD_BATCH_REMAINING_AND_AGGREGATE_FOCUSED_V2.json` | PASS: all 12 corrected range tests plus 389 signed-display tests, 73 explicit subtests; exact composed 1,207-node axis | `84b9beb2e774e8f3bd0dc0ac98dc0426af51454e2b94ed9ceffde1902c52e56c` |
| `f39-import-format-focused-20261023T074900Z/F39_FINAL_FOCUSED_COVERAGE_AFTER_IMPORT_FORMAT_V3.json` | PASS: reran all 65 tests in two import-formatted modules, bodies/import bindings checked, all other tested bytes retained | `c9844918a7a43d0f08a6d1c4ade7cdf9d84debd5db93720a63033d220f012fe1` |

Final coverage: **1,207 normal test nodes and 73 explicit subtests**, with
source/Git stability and actual evaluator import-origin checks. Python 3.12.3
with `-B`, fresh private pytest basetemps, no pytest cache reuse. Ruff passed
for the evaluator and all four new test modules; `git diff --check` passed.
These are focused development results, not full-corpus/financial acceptance.

## Actual original database probe

Receipt:
`/srv/bctc-receipts/f39-four-original-period-memory-probe-v2-20261023T063200Z/F39_FOUR_DOCUMENT_ACTUAL_ORIGINAL_PERIOD_MEMORY_PROBE_V2.json`
(803,709 bytes), SHA-256
`cb2aea947f331e605bc1d4526bb699e31474598984647d56de896a967758a01d`.

One authenticated original-source context loaded 178 selected pages across
four documents. Baseline proof/census/page/table identities matched retained
evidence, original records/censuses stayed unchanged, and the source/input
barriers passed. Only the five proposed function ASTs ran in child memory;
the activated production ASTs were separately checked identical.

- Full110: **NVB**, separate Q1/2025, period proof becomes complete.
- Full117: NVB, consolidated H1/2025, period proof becomes complete.
- Full169: SHB, consolidated Q1/2025, period proof becomes complete.
- Full4: ABB Q1/2025 source, remains HOLD; do not infer missing
  scope/comparative authority from filename, proximity or matching values.

These are three document-period improvements across two banks, not three
financially accepted reports. No PDF visual or full financial evaluation was
performed by this probe. Earlier operator text incorrectly called Full110 VAB;
the authoritative source selector is NVB. That label was corrected additively
outside the repo; no source selector/hash/value or period outcome changed.

## Previous authoritative-pair failure is not a PASS

Previous root:
`/srv/bctc-receipts/f39-frontier-export-official-full-common-20261023T011800Z`.

Its FULL271 stage on the earlier evaluator completed with 48 READY, 223
UNRESOLVED, zero NOT_OBSERVED and 211 FINAL mappings. This is historical stage
evidence, not a replay of this checkpoint or a financial seal. COMMON204 exited
1 after 1:10:17, peak RSS 2,399,540 KiB, with root error `OSError errno12` while
reading a registry through the Windows mount. The wrapped "authority is absent"
message did not prove a missing artifact: Windows and WSL independently
rehash the existing registry to
`c98624ac7822b44fa53c055ad094968a7fb11f3e96751a1c06e875b4999c140b`.

Common `stderr.log` SHA:
`9fd270b085b16c115569727bf875aef2777f02f3a18a3c7b6dfc92e64cd9d3e6`;
`time-v.txt` SHA:
`fcdc4ddf8de570004753b0bde0f6454649abeae5b3350fb0927e1cb87dd164b1`.
The wrapper terminal receipt is missing; do not fabricate it. The old boot
ended, and no old job remains. The exact allocation/shutdown causes are not
fully proven. Additional root probes and Claude tests overlapped; no single
task is asserted to be the sole cause. Full/common original database source
integrity contexts passed after the incident. All failed/partial artifacts
remain preserved; no automatic corpus restart was performed.

## Runtime and remaining work

Root and Claude now use explicit serialized execution leases: a temporarily
empty process list is not a release. A hidden Windows WSL keepalive was started
and verified; metadata showed that the previously added 4-GiB swap was not
active after reboot (only the default 1-GiB swap was active). Do not read, hash,
copy or upload swap contents. Review metadata and restore resource readiness
before another long replay. A byte-verified ext4 working-copy proposal exists;
it is not yet executed/accepted and may need updated checkpoint pins.

F39 still needs fresh authoritative FULL271 and COMMON204 on its final code,
independent replay, exact observation/storage/projection and semantic-axis
checks, SQLite integrity, whole-source/cell/residual/PDF audit and a truthful
terminal ledger. Known algorithm holds, including unsupported period layouts,
must remain visible, distinct from genuine source conflicts. Do not open a new
F39 research batch as a prerequisite to starting the user-authorized F36 work.

F36 next: inspect coordination and current worker branch pins, review the
seven coherent semantic commits, independently run focused regression, then
promote only reviewed changes. Historical F36 audit builders can synthesize
manual-review/genuine-source-ambiguity labels: never treat generated text as
actual review. Reuse verified unchanged evidence, retain algorithm gaps as
such, and produce fresh diagnostics/coverage before authoritative acceptance.

Frozen shared SHA-256 pins remain:

- evaluator: `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`;
- generic runner: `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.

No migration manifest/base history was rewritten, no S3 objects overwritten or
deleted, no provider invoked, and no canonical Excel/family completion claimed.
