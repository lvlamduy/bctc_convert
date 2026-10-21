# F39 original cell census and quoted tax root checkpoint

F39 now retains an authenticated original raw-cell denominator before family filtering, projection or private repairs. The official runner requires successful source-context exit before persistence and independently rebuilds the entire census and trials from SQLite. It also recognizes the whole PRIMARY label `Chi phí thuế thu nhập doanh nghiệp ("TNDN")` without granting a broader NOTE alias or ancestry permission. All 2,017 focused tests pass; independent replay of 34 source documents preserves the previous final outputs exactly. F39 remains unfinished.

This checkpoint follows `3cd34b74da2da83062f968bbcc7e38c3b1de6c1a` on `codex/f39-income-tax-laptop`, with migration base `8efd618b6c77f0cdbb402a440e7ba3b3549184f1`. Reports remain 2025 through current; standalone 2024 reports stay excluded. Earlier comparative columns printed inside an eligible report remain valid when authenticated. Claude owns the three PRIMARY statements separately; no Claude, shared, F36 or F37 code changes here.

## Original source boundary

`open_income_tax_original_census_source_v1` binds actual read-only SQLite bytes, a held file descriptor, path identity, byte count and SHA, and the pinned index, manifests and selections. It rejects sidecars, unsafe paths, authority drift, boolean ordinals/counts, repeated document loads and reuse across threads/tasks. The context rechecks actual inputs on exit. A caller-supplied JSON object or approval boolean cannot authenticate a source.

The official stream calls the original loader once per document per pass. The same loaded bundle supplies repair/PDF authentication; that callback no longer reloads original JSON. The denominator retains every selected page, section, table, row and original MONEY position, including blank GROUP rows, anonymous TOTALs, quarter columns, nulls, dashes and printed zeroes. UNKNOWN columns remain separately identified in the exact raw columns and rows; digits do not turn them into MONEY. Original BLOB, original-object and validated-object hash domains remain distinct. No financial value, unit, period or disposition is inferred by this census.

Each document is written to a fresh, canonical, write-once `raw-census` JSON file while still provisional. Only successful source-context exit and implementation/input rechecks permit handoff to persistence. The official cold adapter opens another authenticated source context, reads original SQLite again, uses independent indexed query evidence and compares whole census bytes, indexed evidence and complete trials. It returns only after that context closes successfully. Legacy internal fixture/replay calls without this capability make no authenticated-denominator claim.

The full runner additionally stores exact census BLOBs in family-local `f39_raw_money_census_v1`, linked to the real generic family run and trial axis. It commits and closes the insertion connection, opens a separate read-only/query-only connection, reloads every BLOB exactly and runs SQLite integrity checks. Focused tests exercise this mechanism with real SQLite and pinned synthetic corpus authorities. The bounded 34-document witness deliberately does not ingest a fake subset under the full271 index; real full271/common204 persistence remains an outstanding family gate. The generic store is unchanged.

## PRIMARY quoted label and normalization fence

The new whole-label matcher preserves punctuation and requires literal ASCII quoted `TNDN`. Reviewed Vietnamese folding and layout whitespace are recognition views only. Unknown annotations, control/format characters, altered acronyms, extra words and ordinal prefixes do not gain this permission. CURRENT and DEFERRED precedence remains unchanged.

Tests exposed an existing normalization bypass: a fullwidth acronym could disappear entirely, leaving a legacy expanded ROOT label. A PRIMARY ROOT-only raw lexical fence now blocks erased glyphs and empty/unsupported quoted content before accepting a legacy ROOT. The NOTE and ancestry consumers keep the previous classifier vocabulary; the quoted alias does not authorize a new structural GROUP or remove numeric population ancestry. No source row, sign or amount changes.

## Verified evidence

| Gate | Result | SHA256 |
| --- | --- | --- |
| Focused witness | 2,017 PASS across 17 suites; all 1,811 previous node IDs retained; zero failures, errors or skips; actual imports and unchanged inputs bound | `05233eb25e09a6ef22226d39ba1ea6ffba8b30bc2e0234e39b9deb8d2fe4f79d` |
| Focused JUnit | 2,017 tests, zero failures, errors or skips | `4f20da3400f77cc9bd752e486e0c1165d637f33b441c13713afa814d5a81152f` |
| Bounded diagnostic | 34 documents; 18 READY review proposals, 16 UNRESOLVED, 90 final mappings; no persistence | `9df4abc07a80fe7ff7754f8dc33e87076394f2d76cadeb9ec4e15f6d957aa4bd` |
| Independent original-source witness | Whole raw censuses, indexed evidence and trials replay exactly; previous final statuses and full mappings unchanged | `82b49555981aaa120ed4529afc22a718f9ab5d18f7d9a5760172cda568654e9e` |

Exact paths:

```text
/srv/bctc-receipts/f39-original-census-focused-v1-1792623667038-4dcfe0d066f0b8/F39_IMPLEMENTATION_FOCUSED_RECEIPT.json
/srv/bctc-receipts/f39-original-census-source-panel-v1-1792624637221-25dac7a3a2bb28/warm/income-tax-bounded-diagnostic.json
/srv/bctc-receipts/f39-original-census-source-panel-v1-1792624637221-25dac7a3a2bb28/F39_ORIGINAL_CENSUS_34_SOURCE_REPLAY_WITNESS_V1.json
```

The source witness retains 2,170 pages, 3,249 sections, 2,959 tables, 24,894 rows and 83,060 raw positions: 71,203 MONEY positions and 11,857 non-MONEY positions, including 543 UNKNOWN positions. There are 891 pages without a MONEY cell. These are whole-source denominators, not F39 relevance, mapped-cell coverage or acceptance counts. All dispositions remain unclassified. The observation contract passes separately; its recursive mapping checks are not this denominator.

Warm loading remains 34 original-JSON API calls, 2,170 rows and 10,196,448 payload bytes, with 2,169 exact replays and the existing one lossless redundant-TEXT normalization. The independent cold adapter uses no base-cache object; its inventory counters are not exposed or instrumented by this witness. Measured warm and cold stages were 276.51 and 238.23 seconds on this run; these are not a speedup claim. Source DB SHA remains `ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`, 573,145,088 bytes. Read-only/query-only `quick_check` is ok and `foreign_key_check` is empty before and after; source/PDF/authority/code/test/census bytes remain unchanged.

Actual LPB74 p6/s1/t1/r19 supplies the quoted-label source witness, with page SHA `58fc21dc35acc919093abc22e89750324ff4904973a5e070cae4f833ec0a9007` and table SHA `8cc7794642f60e440c7593b5b039bf4d047eb392542b65b4fe935557d63e87b1`. Its lexical role is now ROOT. This grants no schema mapping, ancestry, scope or amount permission; LPB74 still has zero final mappings.

The 206 added cases cover the raw boundary, actual stream/cold/store path, quoted recognition and adversarial resealing. Earlier failed runs remain intact: the first targeted invocation lacked a temporary parent directory; subsequent runs exposed invalid fixture assumptions and the fullwidth normalization bypass. In particular, current recovery returns `PRIMARY_INCOME_TAX_SOURCE_ROWS_NOT_LOCALLY_USABLE` even for an unrelated no-anchor source. New tests record that exact algorithm HOLD rather than fabricate NOT_OBSERVED. The corrected four-case JUnit is green, but its shell launcher exited1 because of CRLF and is not treated as a successful witness command. The subsequent complete 2,017-test witness exits0. No old test is removed or skipped. Ruff and `git diff --check` pass.

## Remaining family work

The denominator is not the all-status disposition resolver. A future resolver must bind each relevant original position to one primary disposition, keep proof/control uses separate, handle original-to-private-repair coordinates explicitly, and count only final selected mappings as exported observations. UNKNOWN positions and unresolved relevance cannot disappear into coverage totals.

CF caption ownership and the two-locator PBT/tax-to-PAT bridge remain inactive implementation work. The original LPB p7 table unit is null; its four MONEY headers explicitly print `Triệu VND`. Future unit proof must use those actual headers, not invent a table declaration. A positive same-statement continuation relation must not be confused with UNKNOWN report scopes matching each other or with permission to export unknown scope.

LPB p64 still has two distinct prior-period-adjustment observations: `8.966/4.829` in recognition table t1/r3 and `9.035/4.829` in effective-rate reconciliation t2/r4. They are adjustments, not the two totals; both anonymous totals print `1.233.989/1.198.535`. The page30 tax definition does not select one observation or prove a genuine same-basis issuer conflict. Schema 5733 remains under 5737, with a reconciliation precedent; no recognition-only shortcut is approved. SSB187 numeric outline evidence also remains inactive; no global numeric stripping is enabled.

F39 still needs full271/common204 evaluation and real persistence/reload, complete source/disposition and observation contracts, source replay, SQLite integrity, PDF/residual and projection audits, and its final release ledger. F36 then F37 follow after F39 is terminal. F41 remains closed. No workbook acceptance or READY_FOR_INTEGRATION is claimed here.

## Implementation pins and checkpoint handling

| File | SHA256 |
| --- | --- |
| F39 evaluator | `7adb6a8a8c8d639265d7d5c063bc7928856e9aa233bbc3c13c03501eadad694b` |
| Original raw census module | `200d57cd8bdadcc87a4741c25bfe53f89ff59371063927a680461122d88059cc` |
| F39 runner | `a6be987c2fde7bbf4636573eb5b419265ffd7cb8027f589184719204099dcd23` |
| Signed-display tests | `bcf3770f56dc2fdea214819ee3ec2ad9ffc481e97e9f7d43e87eb3c54774d38d` |
| Raw census tests | `fa35ac4e300c35cc399eb900d8df670e8655c6cc8e61b7c2ae6f8a6917707a2f` |
| Runner tests | `74517b4bd14f2881ac9e0cc638d1bb7420dadb3952d92c4fdf406a19699bbb0a` |
| New focused helper | `7a718e4c001dccc8efd2a49d1e5c0043b18b9f3213dd6f7b4eb7d2af0884fd7d` |
| New independent source helper | `589a44816793eed21d2acb3fb9d44b29de26f0ae2f4201457917d574ce6495ed` |

The runner also pins both authority validators used by the new source boundary. Frozen shared evaluator SHA remains `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`; frozen generic runner SHA remains `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`. No restored source/database write, provider call, obsolete OCR, artifact cleanup or common-branch push is introduced.

Both witness jobs reached terminal PASS before documentation or Git mutation. Tests bind the preceding HEAD and exact changed source bytes above; their historical Git fields are not rewritten after commit. The precommit event is `bctc-ai/coordination/2025-current/v1/events/20261021T233125030622Z-LAPTOP_INTEGRATOR-HEARTBEAT-3ee8ad24e39441e4957bc381fc6ce36e.json`, VersionId `wXf16D_3T720RnasQdnBgg0VwlWBg9a4`, SHA `e9d8f75516550577131bccb091b3abb8148801411924ed3e7c410b32ec10efca`.

Commit and push are restricted to the owned F39 branch. Any subsequent evidence publication must use reviewed append-only tooling, fresh object keys, checksums and exact-VersionId readback. Actual publication receipts and later coordination events carry the resulting keys; this document does not claim that an upload has already completed or that these witnesses are a complete machine backup.
