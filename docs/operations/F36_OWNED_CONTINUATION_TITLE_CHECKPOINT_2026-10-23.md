# F36 owned continuation-title checkpoint — 2026-10-23

F36 remains **UNSEALED**. F39's user-authorized unsealed checkpoint remains
preserved; F37 is unclaimed and F41 remains closed. Scope is reports from2025
to current, with printed comparatives retained. No provider was called.

## Promoted change

Algorithm checkpoint `4a5eec65aed1b0fc7a6e233cfb198e28f73b6736` on
`codex/f36-operating-expense-laptop` adds a finite, source-bound continuation
title to the existing complete-owner projection. It descends from pushed
printed-root checkpoint `b4b521329e828870d32697e19b3431c1f3dc2a63`.

The new title authority is only the whole configured owner, an optional positive
ASCII note ordinal, and the literal parenthesized `(tiếp theo)` marker, allowing
NFC/case/layout equivalence. Every present prior owner title must parse fully;
owner and printed ordinals must agree. Other-family titles, extra scope prose,
competing owners, malformed raw characters and missing markers do not qualify.
F36 snapshots literal aliases before the generic compiler normalizes them.

Existing same-source/adjacent-page/selected-axis, period, unit, terminal-total,
frontier and inverse-source checks remain in force. The title grants no period,
unit or numeric value. The two frozen shared files remain unchanged/read-only.
Only the F36 evaluator and one new test module changed. Payroll, performance,
PRIMARY-witness repair and Claude's experimental notes engine are not promoted.

Private reviewed commits `1703c9e2bf8ec5e180ee0d5ddcbd99abe620adf4` and
`28d85dcd73ffc9a741a15bca1f24381d935bc876` were cherry-picked with provenance
as `1d0c0b54` and `3213981c`. Final style-only commit `4a5eec65` removes one empty
line after imports; production/config/scripts/tests match the tested candidate
when blank lines are ignored. Production evaluator SHA-256 is
`f1c84d97c4e435f47fbab7a3ac708d4651af9c7d5cfdd81ac484e71105cbc771`.
Final test SHA-256 is
`3059163da382cee12487478cfd97cd175fd0352a0b77de88717bcf3d48b4e5f1`.

## Actual validation

- Focused gate: **721/721 normal tests PASS**, no failures/errors/skips,
  exact collection/report/module axes and unchanged inputs/import origins.
  Receipt `/srv/bctc-receipts/f36-title-only-full-focused-v2-20261023T124400Z/F36_TITLE_ONLY_FULL_FOCUSED_V2.json`,
  SHA `f1cf50d44ac5077e551cd30bec2c6493e03e926bff024204c5ddd5111ae9dacc`,
  1,920,489B. Peak RSS181,004KiB. Ruff PASS after the one-empty-line fix.
- Retained previous focused gate:719PASS/1FAIL, SHA
  `6f863ac8c7349b489532ee55e84ab68b8d9930dd600057b05ca4878693c7e437`.
  The new negative incorrectly rejected sender `NONE`, an established positive
  in the complete-owner route and Roman-quarter matrix. Only that test contract
  was corrected: receiver `NONE` is now the true negative, plus an explicit
  source/receipt/replay positive for sender `NONE`. No production marker gate
  was relaxed. Its final `inputs_unchanged` barrier was true.
- Actual FULL149 SGB source comparison: baseline UNRESOLVED/zero mappings became
  READY/13 mapping **proposals**, reasons empty. Both fresh interpreters used the
  same complete46-page original selection. Source-context exits, original
  document/page/BLOB axes, public replay and observation contract PASS.
  All13 final mappings match original inverse locators/text;14 projected rows
  preserve raw values/column ordinals. Owner28 connects p34/s6/t1 to p35/s1/t1.
  Final root is printed p35/s1/t1/r6 `484.249 | 445.036`, with exact frontier
  closure; no derived root is exported. Independent review GO.
  Parent receipt `/srv/bctc-receipts/f36-full149-title-semantics-20261023T124900Z/F36_FULL149_TITLE_CONTINUATION_SEMANTIC_COMPARISON_V1.json`,
  SHA `ef04119df7ed1043d7b1c66a0f1035cd4dafa514fdfc9420830239052cd97a18`,20,482B.
  Baseline child SHA `3769ed11f5e9c10c68dfd6ffd9e768e4a66e2048ee3561d381baa7e956ac3c5d`,1,111,082B;
  candidate child SHA `de889c016a64a1cfa9e8192baccf0a7eb41d93c72dc74ce612e35a49017ab3b4`,1,419,459B.
  Independent cold replay, financial acceptance, result-store persistence and
  full PDF/residual audit were explicitly **not performed** by this probe.
- Before promotion, exact-version S3 coordination review read180versions/latest
  events, stable inventory and active claim, with no new F36 owner conflict.
  Receipt `D:/bctc_bank/restore-receipts/f36-pre-promotion-coordination-20261023T125104437245Z-a609326cd8624627b267f16df738f9f7/F36_PRE_PROMOTION_COORDINATION_REVIEW_V1.json`,
  SHA `112a83df43fb3df19f4bcba39caa444803abed874f017eca2e0f2e42f64255d9`.

## Source gaps and next work

A bounded original-database probe and manual full-page PDF inspection found
FULL243 PRIMARY p6/s1/t1/r14 contains three printed cells absent from original
JSON. PDF has `'(225,316)','(228,343)','(225,316)','(228,343)'`; JSON retains only
the first cell. The page explicitly uses million VND. Other PRIMARY pages use
VND, so whole-document/PRIMARY unit context is mixed and remains unusable.
The note p42 itself has no local unit. No missing cell was filled or inferred.

Additive manual evidence:
`D:/bctc_bank/restore-receipts/F36_VAB243_PRIMARY_PRINTED_CELL_GAP_MANUAL_REVIEW_20261023_V1.json`,
SHA `1c32b36775c8038cb12bccfb70a408e0fa9915d6224fba2ab8b773eada897a3d`,14,535B.
It binds original unit-controls receipt `4c0694e064819dd7cf8540650d6d3bcf56529ff2dbe096a2e35c789aa0ab0b6f`
and render receipt `4f004e6192cf50666036593d25c0b58efba0525a881b1b5818c4ae726b527db5`.
This is not a registered repair, unit assignment or acceptance receipt.
Existing DASH-only/component-table repair rules cannot authenticate these
PRIMARY numeric omissions without a separately reviewed family-local extension.

Next: strict payroll-alias scope, typed source-backed PRIMARY witness repair,
and isolated performance validation. Use bounded real-source cases before a
fresh authoritative full271/common204 pair on the final coherent batch.
The older full/common pair is a baseline with coverage violations; its successful
execution does not seal the current code. Final source/cold replay, observation,
SQLite persistence/integrity, PDF/residual audit and family ledger gates remain.
Preserve all prior artifacts and failed runs.

## Immutable backup

Checkpoint `54638a6938112db5a815a6581cd108ba8773391a` is pushed and remote-exact.
Twenty pinned evidence/image/helper/input objects plus one nonterminal HEARTBEAT
were uploaded with conditional create-only PUT, AES256, SHA checksum and complete
exact-VersionId byte readback. No old object was overwritten or deleted.

Bucket `test-s3-duylv`, region `us-east-1`, prefix:
`bctc-ai/coordination/2025-current/v1/artifacts/LAPTOP_INTEGRATOR/f36-owned-title-checkpoint-20261023T130719937314Z-4f3bfd121c8644e9b641d84bb8b167ae/`.

HEARTBEAT key:
`bctc-ai/coordination/2025-current/v1/events/20261023T130719937314Z-LAPTOP_INTEGRATOR-HEARTBEAT-7333323a5a314c34bacd3eb0c9be6b2a.json`,
VersionId `bYU22GxaxVsaqS3i_qoY1VEANBe5K3tV`, SHA
`23381c1109385fb30a138b2d258490e1fb5363ce98234ac8067223223f58e6c1`.
The focused721 object's VersionId is `AZAAD.HsPWv9ZsfqqZNwyskdUU_lY5ny`.

Local publication receipt:
`D:/bctc_bank/restore-receipts/f36-owned-title-checkpoint-20261023T130719937314Z-4f3bfd121c8644e9b641d84bb8b167ae/final.json`,
SHA `39d23446047daa6a5d1710b0d104125d64627d02cc92a370e91c694270b13521`.
Publisher SHA `a8ffed515309746cfb969fab8bbe808660b2058fd46d1511aa78959196d78918`;
publication-inputs SHA `cf7a37095436fae0369d9c8b15a3205c866b527b55bb805ae55fac8d841d716d`.
The heartbeat explicitly retains F39/F36 unsealed, F37 unclaimed and F41 closed.
