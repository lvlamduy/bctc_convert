# External draft: pure ROOT closure and actual T-packet compatibility — 2026-10-25

This checkpoint integrates the reviewed two-path pure table-source closure API after actual254 tests and both real-packet checks, following e3bb826089f227ae4d122d85a79274c762753e21. It is opt-in structural validation. Existing diagnostic producer, default dispatch, mapping and exporter code remain byte-identical; their earlier full/common artifacts keep their original head/config authority. No broad producer rerun is claimed for this additive pure API. Financial/canonical ledger and family acceptance remain separate.
F36/F39 remain UNSEALED; F37 unclaimed; F41 locked. Provider0;2025-current scope and printed comparatives retained.

## Frozen source and actual focused gate

Current-base candidate `69fe05d095f1d1d7d93e6e993da59af2be44acbb`, base main e3bb above.
Owned branch `codex/notes-root-closure-currentbase-draft-20261025`.
Runtime clone `/srv/bctc-receipts/notes-root-closure-69fe05d0-private-20261025/repo`.
Exactly two new paths; their bytes equal corrected Claude source commit `242b41416d5753fd612acfce8ed345095ebf85a9`:
- `src/bctc_ai/notes/root_closure_v1.py`: SHA `8e3dd7f40001475076af48a84e5ff79d4073280ffafa777e96c36edecfd34214` /15,912B.
- `tests/unit/test_notes_root_closure.py`: SHA `cf783b2ebf33759f6684ead21f79637bd6e1340f86fe55315f5d2ecd9e725519` /15,654B.

Root actual focused receipt SHA `3b02b5ed1b8cd50a2469b070c0cb2ce903071c6f44fff4d61d2e57d6cc9ea5f5` /1,723,999B:
254 normal tests PASS (old214+new40),0 subtests, JUnit254 declared/254 elements; compile/Ruff31 PASS.
All2166 source references plus2 control refs and12 actual origins unchanged; peak RSS103,392KiB.
Case `restore-receipts/NOTES_ROOT_CLOSURE_INTEGRATED_254_CASE_20261025_V1.json`, SHA
`099ce437ac4caee07ed6da17d2d6be8ca8fd0f8ed136f1ca66206f3231ddaaae` /295,430B.
Focused helper SHA `dfa6d8ca410566149c1ae78c5efa5fb149730f720ffbfbd6c22039b902c89db7`.

Retain earlier `8befe8b201ae3890825686aec39aa28929d1b613` unchanged: UNRUN schema-mismatch draft,
not an actual failed source run. It read neutral `fields` envelopes as scalars;242 unwraps strict `{present,value}`,
requires plain-bool presence and keeps missing distinct from explicit null; old37 assertions plus3 controls retained.
Retain actual-check V1 helpers unchanged and UNRUN after static NO-GO for releasing input FDs before final verification.
V2 corrects that lifecycle; no source/PDF/amount repair was made to obtain compatibility.

## Real source-reference packets — actual builders

Builder `restore-tools/build_f36_t_changed_table_packets_v1.py`, SHA
`afbd60d862de7719aed7bd746da239abf7f6a0e94aceaa1048295e1fff84eef2` /21,907B.
Case `restore-receipts/F36_T_CHANGED_TABLE_PACKET_CASE_20261025_V1.json`, SHA
`bfc0a2205e659d7e72d70ac513a285bca711427aecaff2b4edc6a276998c3fc6` /3,399B.
Receipt basename below is `F36_T_CHANGED_TABLE_PACKET_BUILD_V1.json`:
- FULL directory `/srv/bctc-receipts/f36-t-real-table-packets-full271-20261025-v1`:
  SHA `8aeff5e2736b55f9904b522c83bbfbacb20d583a2512aaceca4f470537a6b923` /9,520B;36 packets;
  CPU16.377s/RSS28,544KiB; full neutral counts, final FD barriers and exact source joins PASS.
- COMMON directory `/srv/bctc-receipts/f36-t-real-table-packets-common204-20261025-v1`:
  SHA `e5d7fdda7c9b5ce9b1f874d5725fed315cefdcdc9bce6bc604a9d2379fce299a` /8,167B;29 packets;
  CPU11.055s/RSS27,328KiB; corresponding neutral counts, final FD barriers and exact source joins PASS.
Packets retain real ORIGINAL envelopes, all rows/columns/fragments and separate hash domains; amounts remain unavailable.
No reconstructed values, source edits, closure verdicts or financial permissions were inserted by the builder.

## Actual V2 compatibility (TOPOLOGY_ONLY_NOT_ACCEPTANCE)

Helper `root_closure_actual_check_v2.py` SHA `46fa8023ff0a5fc238c78b8818eadbe2cadec8d5b1263a9c010ac87993fa443c` /14,066B;
control `root_closure_actual_check_v2.sh` SHA `12b1aa08c152fa41cf4c5ca40c425f73777be39631ee8492fa0e734f4dfd7812` /4,963B.
Paths below are relative to each literal retained root; summary/results are under `out/`.

FULL root `/home/bctc/notes-compare/root-closure-actual-full271-69fe05d0-20261024T200156Z`:
- `terminal.json`: SHA `ab2693e34e8af85dff83ad58ff7e3322217f0aff02f8ac9375cbb4ba1d7f99f8` /418B.
- `out/summary.json`: SHA `1ec4ad3cdfeddfd4afd0a13bca4d7c9eab7c8b40e4cff0f1c0c6a9bd6c250364` /712B.
- `out/results.jsonl`: SHA `40e357b31b6d394f9f6ac2fee3bfce0654b99eeab83ce5c2dff8da4184855874` /51,386B.
36 EVALUATED tables;68 ROOT_CLOSED lanes;4 NOT_ROOT_CLOSED:ROOT_EQUATION_NOT_EVALUABLE lanes.
Predeclared FULL69 physical64 positive closes both lanes. All37 held build-receipt/packet inputs final-checked.

COMMON root `/home/bctc/notes-compare/root-closure-actual-common204-69fe05d0-20261024T200211Z`:
- `terminal.json`: SHA `61b178bef0a26cea8c1da967e61cd10738532ea60cdc0d1505132375a1851805` /420B.
- `out/summary.json`: SHA `fddaad9197a0bb999ca6af451310a17ce278585d7288bef58ec66336dab541ff` /683B.
- `out/results.jsonl`: SHA `25eae0156b4b76d75a0c40bf1c584a4866b66cd2772c851dd3e149651493ed29` /41,033B.
29 EVALUATED tables;56 ROOT_CLOSED lanes;2 NOT_ROOT_CLOSED:ROOT_EQUATION_NOT_EVALUABLE lanes.
All30 held build-receipt/packet inputs final-checked. Both profiles: genuine unit/source-axis before+after,
packet held-FD before+after and helper-byte barriers PASS. Missing source operands remain unresolved, never zero.

## Interpretation and pending breadth

ROOT_CLOSED proves this pure API's complete source topology under bound input artifacts, not period/unit/scope,
role/RNID, canonical mapping, source/PDF financial conclusions or family acceptance. F36 mandatory ROOT policy
must not be imposed automatically on F39 optional-root outputs. No unknown amount is manufactured from hashes.
Hash domains stay explicit: stored page BLOB2LF; raw-value canonical JSON1LF; notes table compact JSON0LF.
ALL_OPEX1638 FULL/1208 COMMON packets and their broader closure review are next, UNRUN at this checkpoint.
Canonical ledger/core/backlog partition, legacy disposition, export/store gates and PDF/residual audit remain PENDING.

Legacy contract correction: coefficient is the full parsed signed integer, not a sign multiplier. Final values are
canonical semantic lanes; pooled source refs may be corroborations, not additive components. Never zip final value
ordinal to every ref's column ordinal. Outer selected-candidate table receipts DO serialize lane→column/source-period
axes, but missing, ambiguous, transformed or incomplete evidence remains explicitly unresolved; no amount-based match
or period inferred from document year. This does not displace independently proved current notes/ORIGINAL evidence.

All2166 integrated source SHA/size pairs equal the actual254 worker receipt; frozen hashes and Windows read-only attributes passed. External projection verification 0d6cfa94f5592a81e9a3cbed51d8f45791ae9038c7982ea72764eaad386caf57 (440B). Fresh193-version S3 coordination review before this mutation passed42a1ef2e184acc93c46977734c3542b8b051af4d189e3b56a1962533812dfa31; no competing F36 owner. Source equality does not rewrite the worker receipt as a main-HEAD run. New artifacts are LOCAL_ONLY; no full backup or family seal.
