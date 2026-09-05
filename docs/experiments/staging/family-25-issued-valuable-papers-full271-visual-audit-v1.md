# Family 25 — issued valuable papers full271 visual audit v1

This ledger seals Family 25 (`ISSUED_VALUABLE_PAPERS`) on the immutable
2025–2026 corpus. No provider was called. Source PDFs and selected page JSON
were read only. Results remain experimental schema-mapping proposals and are
not canonical/export authority.

## Authenticated inputs

- Full271 manifest index:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`
  (422,971 bytes; SHA-256
  `969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`).
  Its frozen page store is 573,145,088 bytes with SHA-256
  `ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`.
- Common204 manifest index:
  `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json`
  (317,566 bytes; SHA-256
  `acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1`).
  Its frozen page store is 553,984,000 bytes with SHA-256
  `a14904a492e6beae165b81f7aa1738352a9824e113f1b163a46ee277d37e0220`.
- Initial full271 baseline:
  `/dev/shm/f25-full271-baseline-v1.json` (44,048,217 bytes; SHA-256
  `b2269d9ed446b34ed34ea1f72b450a48de3f5bfcce80c82c35b8a87df4148572`).
- Frozen shared evaluator SHA-256:
  `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`.
  Frozen generic runner SHA-256:
  `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.
  Family 25 did not modify either shared file.

The two registered historical eight-bank artifacts contain 16 distinct source
SHAs. They have zero source-SHA overlap with full271 and are authenticated as a
disjoint safety oracle, not used as current-corpus value authority. Comparator:
`DISJOINT_EXPANSION`.

## Baseline and terminal results

| Corpus | Documents | READY | NOT_OBSERVED | UNRESOLVED | Mappings |
|---|---:|---:|---:|---:|---:|
| full271 baseline | 271 | 101 | 33 | 137 | 494 |
| full271 terminal | 271 | 270 | 0 | 1 | 1,438 |
| common204 terminal | 204 | 203 | 0 | 1 | 1,067 |
| full-only expansion | 67 | 67 | 0 | 0 | 371 |

All 33 initial false-N documents and 136 of 137 initial unresolved documents
became READY from directly observed presentations. The one retained U is a
genuine source-unit ambiguity described below.

Full271 identifiers:

- run `gjfafstorev1:run:405b665e1dcf485edcb977e4c4e6e267fc2ccbf4fef103708848fb4ed8fab3b7`
- sweep `gjfafsv1:sweep:18c6aef04b7a840781a99a05e38cf800979e1cded695f5b47bc1363034a43855`
- audit `gjivpfeav1:audit:9c146e7a51b2e782c583f5fcab0aad85fbdb3685129230476243b0e522df0dda`

Common204 identifiers:

- run `gjfafstorev1:run:d19c3ecd519a4b75c661aa4d67e5609993ca5fe2d7c55d3fb7610a420d97dfee`
- sweep `gjfafsv1:sweep:8e08db1535456182c32318e8b7c4373285041ffb6c5e34e23718f3d9e99df8c2`
- audit `gjivpfeav1:audit:d66589799a47a17a82f0afd01b663183fdb263eef08df01605cd5a0bc551d008`

## Complete visual and source-only gate

Every baseline N/U presentation was visually checked against its source PDF.
Important formerly blocked shapes included the following:

- ABB ordinals 3–12 print three instrument face-value blocks with direct tenor
  rows. Missing selected-JSON dashes were accepted only after exact PDF-bound
  repairs; blank cells were never solved as zero.
- SHB ordinal 167 page 45 first repeats one face-value summary and then prints
  a complete transposed bond/CD maturity detail. The summary is pruned only
  when every lane equals the detail's two terminal equations.
- STB ordinal 203 page 32 prints an internal owner row, separate bond and GTCG
  three-tenor populations, two visible `Cộng` subtotals, and final `Tổng`.
  Exact all-lane equations map the two printed parents and root, producing all
  nine roles. The owner and group rows are null-valued structural carriers.
  Owner mismatch, non-null owner values, hierarchy reset, nonterminal root,
  row-kind drift, or any equation mismatch fails closed.

Full271's audit contains 395 source-only rows. Of these, 349 are consumed only
as exact equation controls. All remaining 46 locators were dereferenced back
to the frozen selected page JSON: 38 are null-valued `GROUP` rows and eight are
null-valued `ITEM` rows. Zero has a visible/nonblank money cell. The canonical
raw dereference axis SHA-256 is
`0fd90f6f39767651d4c7ff2d3ae96969cd3527a8ce91f8a9b8bdbb973f2d4a66`.
Common204 has 249 exact-equation controls and 29 other source-only rows; all 29
are all-null (22 `GROUP`, seven `ITEM`), with raw axis SHA-256
`7ef349519b5862dd66f610ab94141ecd7a192acdbdd643b0d3af9d447a78db8f`.
No PDF-visible schema-mappable row remains N, U, or source-only.

## One genuine unresolved source conflict

Full ordinal 255 / common ordinal 193 is
`vietstock_bctc/VAB/2026/BCTC Q1.2026 RIENG LE_0001.pdf`, source SHA-256
`00dc1e49a068bacbfaf36d4d337916adc0e3737c28f5bf0cf93828b20774f967`
(11,610,064 bytes). Physical page 39, selected page JSON
`gfpstorev1:json:8dbaa964404bf8f88e56c8c84d18d1a1f859ee4ee0979a4c9b585ea982876767`,
section `s3`, table `t1`, visibly prints current/comparative rows
`[4,000,000, 3,500,000]`, `[-, -]`, `[1,458,830, 1,458,831]`, and total
`[5,458,830, 4,958,831]`, but no local unit.

The same document contains both VND and million-VND accounting contexts. The
compatible primary-owner observations are VND
`[5,458,830,500,000, 4,958,830,500,000]` and million-VND
`[5,458,831, 4,958,831]`; the note total equals neither exact two-lane axis.
Inferring a unit would require rounding/backsolve, so the trial correctly stays
`FRAGMENT_PERIOD_OR_UNIT_AXIS_NOT_LOCALLY_USABLE`.

The page was rendered directly at 300 DPI, RGB, PNG, no alpha, 2475×3542.
Image SHA-256 is
`1ef17f82f3412385405a22d112a8dfd24f9fc034a9a0d8a803853d1e9df53b94`
(1,029,038 bytes); render-receipt SHA-256 is
`e521de04790b990b0bbfa696776986235791663a654cd550257475ac268a6c9f`.

## Source repairs and null safety

The registered artifact contains 28 exact `null` → visible-dash repairs over
nine PDF/source-page pairs: ABB 15, SGB eight, TPB four, VAB one. Each entry
binds source path/SHA/size, physical page, selected page-JSON version, table,
row, column, 300-DPI full-page image SHA, crop RGB SHA, before null, observed
PDF glyph, and after dash. Repair-axis SHA-256 is
`4413fe24d7030ebcbbaa296523781a72a30ca072536966b5c038cd3ffdffccfb`.
Out-of-scope repairs are skipped; any in-scope byte, render, crop, locator, or
before-cell drift fails closed.

Equations corroborate or veto observations only. Null never enters a sum and
never becomes numeric zero because an equation closes. A visible dash maps to
`DASH_ZERO`; a missing dash is usable only through the authenticated registry.
An observed sibling lane is retained while a blank lane remains coefficient
`null` / `BLANK_SOURCE_CELL`; an all-lanes-unobserved role is omitted.

## Source-observation and differential contracts

| Corpus | Mapping occurrences | Cells | Partial | Source blanks | Derived | Violations |
|---|---:|---:|---:|---:|---:|---:|
| full271 | 2,876 | 5,436 | 18 | 18 | 754 | 0 |
| common204 | 2,134 | 4,068 | 14 | 14 | 550 | 0 |

Both contracts are `PASS`. Counts include the candidate and authenticated
stored-source replay occurrences. The store reauthenticated implementation and
repair bytes, rebuilt every trial from the frozen database/frontier without
access to expected trials, required canonical equality, and reauthenticated
the bytes again after callback return.

Common204's 204 source SHAs are an exact subset of full271. After removing
corpus-relative document IDs/ordinals and content-addressed mapping IDs, all
204 status/reason/mapping projections are equal. Both subset axes hash to
`64df972c77446108e5ad91c73103ee8da19621c2434bfcf25eacd7020741f1eb`;
semantic mismatch count is zero. The full271 semantic axis hashes to
`1384f97843694eed2f8e0cd71ab1f4ac57e5dc519ea11c77b95929179ef5d23d`.

Against the immediately prior 270R/1U checkpoint, 270 source semantic
projections are identical. The sole change is STB source SHA
`653a4124dc782bc56ff3dd95a7d4f51ff14d7fcfcbac65e504947cc62cac8518`,
which increases from six child mappings to nine mappings by retaining the two
visible source subtotals and final source total.

## Release artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `/dev/shm/f25-full271-bb319-final-v2/family25.json` | 59,241,770 | `3bb90af13bf4326bfc6b33c119be187d4547de4d8a99ae736adb0cdfcea4bc4c` |
| `/dev/shm/f25-full271-bb319-final-v2/family25.audit.json` | 4,460,903 | `37ccf21cb5d3db8d596a051d2c5cfe8b163a76a38e004e3229adf671b53ddb4d` |
| `/dev/shm/f25-full271-bb319-final-v2/results.sqlite3` | 99,962,880 | `404226138a854a67458fb73787adf8a23942acee065de3706af0d3ea74851284` |
| `/dev/shm/f25-common204-bb319-final-v1/family25.json` | 44,874,955 | `7882562591c1743ea86b4f942d3d66b817416744fcf2ef9ff2dbd26ce9c71aa0` |
| `/dev/shm/f25-common204-bb319-final-v1/family25.audit.json` | 3,317,698 | `4476176b7f3e4ecfe0b7ea931ef24289e8a81753f1eb3ff526b4ab2c7d6a3165` |
| `/dev/shm/f25-common204-bb319-final-v1/results.sqlite3` | 75,235,328 | `25b6470661d604c9a1ff7a133c038229a67f2c20e535ad7476115a0572b589e7` |

Both SQLite artifacts pass `PRAGMA integrity_check` (`ok`) and have an empty
`PRAGMA foreign_key_check` result.

## Family-local release hashes

| Path | SHA-256 |
|---|---|
| `config/families/tm-issued-valuable-papers-topology-v1.json` | `8f3fe5fd6e33ac6ce572d7aa99212bbe216c8628384119c2fd759409b717d86c` |
| `config/families/tm-issued-valuable-papers-evaluation-v1.json` | `30abf180361d9e16d6b5db539cfa59fd325e75cac3bb6e012141ab22dc6a804e` |
| `config/families/tm-issued-valuable-papers-schema-binding-v1.json` | `992b8b188a1665ac2e61a5a4920841593411e488807f346cbd551c37e5ae0a74` |
| `data/registered/gemini_json_issued_valuable_papers_source_repairs_v1.json` | `9c2e3f09c7730b3e48a4c6d5fac1360e23e3ca27c86627c0778163551a67cd54` |
| `src/bctc_ai/evaluation/gemini_json_issued_valuable_papers_family_v1.py` | `dec79041546f909c3206b081f201b505cc3aa952228a119c7d9f6af26792247a` |
| `scripts/experiments/run_gemini_json_issued_valuable_papers_accounting_family_v1.py` | `7d4b3617ec9e8f422c129b9cbe1a2bc04cf39a513aa41711da32719c9683a4c1` |
| `tests/unit/test_gemini_json_issued_valuable_papers_family_v1.py` | `b4b9365e7a64df0d74b183e9ad4c914d4f6605cdc07f5d6c68fcd34d687da3a9` |
| `tests/unit/test_run_gemini_json_issued_valuable_papers_accounting_family_v1.py` | `23abae826dde00d088334c71413ff88335115b90d4d58f232260ad78d9e16c94` |

## Verification

- Family evaluator, specialized runner, and source-observation contract:
  99 passed in 5.55 seconds.
- Legacy issued-paper builder/variant/scanner static gates: 16 passed; one live
  annual replay was deselected because its ignored calibration index is absent
  from this worktree. The two fixed historical outputs are independently
  byte-authenticated by both terminal runner audits and are disjoint from the
  current corpus.
- Python compilation and Ruff on all Family 25 implementation/runner/tests:
  pass. Family-local `git diff --check`: pass.
- Full271 and common204 runners both performed authenticated source replay and
  exited 0. Both observation contracts and both SQLite integrity gates pass.

## Conclusion

Every baseline N/U and every source-only row has an evidence-backed
disposition. The only unresolved document is a PDF-visible, genuinely
unit-ambiguous VAB note for which exact arithmetic vetoes both available unit
contexts. No visible schema-mappable Family 25 row is left behind, and no
blank-derived numeric mapping is retained.
