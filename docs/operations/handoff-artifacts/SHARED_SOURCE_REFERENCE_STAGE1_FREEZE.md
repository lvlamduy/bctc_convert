# Stage 1 freeze: exact source-reference identity

Freeze time: `2026-09-05T12:51:19Z`

Status: `IMPLEMENTED_UNCOMMITTED_AWAITING_TWO_INDEPENDENT_REVIEWS`

## Authority and worktree

- Worktree: `/dev/shm/shared-source-ref-unique-vps`
- Branch: `codex/shared-source-ref-unique-vps`
- Base and current `HEAD`: `9a01a391dc097283ba436ef01e76ce56d42f4a5b`
- Worktree intentionally dirty with the nine files listed below.
- No commit, push, S3 write, provider call, config edit, database mutation, F30 edit,
  F36 edit, or F37 edit was performed.

## Frozen implementation

1. Added pure `stable_unique_source_refs_v1`. Identity is the complete
   `canonical_json_bytes_v1(source_ref)` payload, never row ID, label, value,
   or digest alone. It clones outputs, preserves first-occurrence order, and
   removes only exact typed-canonical duplicates.
2. Called it only at the two proven semantic origins:
   - F17 `_global_records`, after the two lane selections have accumulated
     record-level provenance and before the reconciled record/omission seal;
   - F16 `_corroborate_identical`, after compatible/equal coefficient-axis
     corroboration and before direct/derived records inherit provenance.
3. Added a family-agnostic final assertion in the source-observation contract.
   Any canonical list of source-ref objects still containing an exact duplicate
   receives mapping-level reason
   `SOURCE_REFS_EXACT_IDENTITY_IS_NOT_UNIQUE` (`lane=null`). The contract does
   not silently repair a survivor.
4. The shared multitable evaluator source and every family config remain
   untouched. It receives the correction solely because it imports F17
   `_global_records`.

## TDD and regression gates

- Behavioral RED: six expected failures reproduced lane duplication, F16
  identical-row corroboration, HTM direct-to-derived propagation, and missing
  contract rejection. The new helper test separately failed collection before
  the module existed.
- Focused helper/contract final gate: `24 passed in 0.11s`.
- Full helper + contract + F16 + F17 + shared multitable evaluator gate:
  `246 passed in 4.22s`.
- Runner/indexed-wiring/repair/storage gate (F16, F17, multitable runners;
  indexed wiring; family stores and document-store pipeline):
  `93 passed in 7.33s`.
- Ruff lint over all nine changed files: `All checks passed`.
- `git diff --check`: PASS.

Tests explicitly cover two numeric lanes becoming one provenance occurrence,
F16 HTM direct and derived mappings, canonical key-order equality, repeated
multiplicity, stable order, typed JSON distinctions, near-duplicates, equal
row IDs at different locators, aggregate/derived/direct survivor rejection,
and unchanged empty/malformed negative behavior.

## Bounded deterministic common204 DB/cache replay

Immutable authority:

- Common204 index SHA-256:
  `acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1`
- Read-only SQLite filename/content authority:
  `store-a14904a492e6beae165b81f7aa1738352a9824e113f1b163a46ee277d37e0220.sqlite3`
- SQLite was opened with `mode=ro&immutable=1`; `quick_check=ok`.

Twenty-four cached candidates were replayed from the immutable page JSON DB:

| Lineage | Deterministic document ordinals | Documents | Mappings | Redundant refs before -> after |
|---|---|---:|---:|---:|
| F16 | all affected `183,186,189,190,191,193`, plus controls `1,2` | 8 | 113 | `12 -> 0` |
| F17 | first current-config READY candidates on common source axis: `1,2,5,7,8,10,11,13` | 8 | 26 | `26 -> 0` |
| F28 shared multitable | first eight base-DB exact-replayable READY candidates: `8,9,11,12,13,14,16,18` | 8 | 49 | `49 -> 0` |
| **Total** | | **24** | **188** | **87 -> 0** |

Every patched candidate passed the new contract. For every included document,
the typed-canonical semantic projection was identical to its cached baseline:

- candidate status and reasons;
- mapping count, `report_norm_id`, role, unit, state, and complete values/cell
  states;
- equation count and all equation fields except the dependent `equation_id`,
  `component_source_refs`, and `result_source_refs`.

Thus the observed delta is restricted to source-reference multiplicity,
physical-vs-synthetic mapping row IDs, and content-addressed dependent IDs.
F28 ordinals `3,5,6,7,10,15,17` were explicitly excluded because replaying
their cached effective-overlay candidates against the frozen *base* DB is not
semantically exact; they are not evidence for or against this patch.

Cache SHA-256 pins used by this bounded replay:

- F16 common204 terminal: `b6a7de27b38539398296cbe92694c11d3b04bfab73516ac3781c848f9e439b68`
- F17 current full artifact filtered to the common204 source axis:
  `2fc5b1581e30d9db53e5d68999062a87bc4170f72f4231738b764b7c98bdfeb2`
- F28 common204: `d9a3c82499adcbe21ce8df09933768c6c93620c0d42bfad0741c5b6242211671`

The helper microbenchmark on a two-ref exact-duplicate vector was 10,000 calls
per repeat for five repeats: `0.155074, 0.151606, 0.150881, 0.151834,
0.152826s`; best `15.088 microseconds/call`. End-to-end bounded replays,
including immutable page loads, took about 1.6s (F16), 1.3s (F17), and 8.4s
(F28 candidate selection/replay).

## Review diff identity

Canonical review payload definition:

1. raw `git diff --binary --` bytes for tracked files;
2. followed in lexical path order by raw
   `git diff --binary --no-index -- /dev/null <path>` bytes for the two new
   files.

- Payload bytes: `19,082`
- Payload SHA-256:
  `60d7182ef459c1ba4560946d9fb082281bdac26fda9d8303ae5d8049f11df87a`
- Diff extent: nine files, 349 insertions, one deletion (including tests).

Frozen file SHA-256 values:

| File | SHA-256 |
|---|---|
| `src/bctc_ai/evaluation/source_reference_identity_v1.py` | `145ce3fa4b31a27ddae6e544e62bb5bcb07a47fd2f93e3c515a8c3aaf64c491d` |
| `src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py` | `7d4728c73dea54075583769ed46f6efd88545020f2ca71948cd40777954a2ea2` |
| `src/bctc_ai/evaluation/gemini_json_other_long_term_investments_family_v1.py` | `71bb05c1da53b5d6c386a8f5ac3e0f9637f63c978b274937f1cb04b44cfaacae` |
| `src/bctc_ai/evaluation/gemini_json_investment_securities_family_v1.py` | `3b1f6db726e7ce84cb440290e48f565293806e0f417fc07a857de64629236b79` |
| `tests/unit/test_source_reference_identity_v1.py` | `44856d906b2cf63654d158c537a5922decb3250e46f9343b31531e4375520a13` |
| `tests/unit/test_source_observation_mapping_contract_v1.py` | `10bbf4b441eb2820cfade272a62aa71f4d967a1a9593f5ee01fa9e7974593e62` |
| `tests/unit/test_gemini_json_other_long_term_investments_family_v1.py` | `935dc016a39ab17501206e70a2891d079fa2c87941a1cffa6a4a63b13f62f0f5` |
| `tests/unit/test_gemini_json_investment_securities_family_v1.py` | `0eb718b6d16ba6198de262ac6b1d8e62aad0816159c46ba649d0fbf6a00b81d4` |
| `tests/unit/test_gemini_json_multitable_hierarchical_family_v1.py` | `4765f93fd3af8094956469515fea56f9dc8ab5ad1583ed3e70741c10ecb5181f` |

## Required staged continuation

1. Two independent reviewers must reproduce the diff fingerprint and review
   helper exactness, the two origin boundaries, the global rejection order,
   and all negative-state tests. Any requested edit creates a new freeze hash.
2. After approval, run a complete current operational diagnostic over all 54
   evaluators; contract rejects every unexplained survivor. Do not infer the
   full271 result from common204.
3. Reseal full271 and common204 independently into additive new artifacts and
   new SQLite outputs. Produce an old-to-new translation receipt keyed by
   source/document/family/RNID/role/unit/period axis; preserve historical
   artifacts unchanged.
4. Verify only provenance, corrected row IDs, and dependent content IDs move;
   run replay, audit, store reload, SQLite integrity/foreign-key gates, and
   exact common204/full271 projection.
5. Only then commit/integrate and perform the separately governed Git/S3
   publication. This freeze authorizes none of those mutations.

Top recommendation: keep normalization at these two proven producer origins
and keep the global contract reject-only. Do not add a generic seal-time repair
or deduplicate by row ID.
