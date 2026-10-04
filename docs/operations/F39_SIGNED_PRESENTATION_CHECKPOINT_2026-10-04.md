# F39 signed-presentation checkpoint — 2026-10-04

Non-terminal development checkpoint on `codex/f39-income-tax-laptop`,
descending from `8efd618b6c77f0cdbb402a440e7ba3b3549184f1` and following
`3c1ed737792f01a095716c525f87858167df1251`. Scope is 2025–current;
2024 remains archive-only outside production. No provider calls, F36/F37
changes, frozen shared changes or immutable-source/config changes occurred.

## Family-local algorithm

Opposite signs are no longer rejected when independent, source-visible evidence
proves that the primary statement prints expense as a decrease in profit:

1. Unique exact before-tax and after-tax profit labels, with source row order,
   must surround an observed signed expense on the same income-statement table.
2. Both final-duration lanes must contain all three observed amounts, with
   printed before + printed expense = printed after exactly. The expense must
   have negative display; no missing amount, digit, sign or root is generated.
3. At least one independently printed non-root tax role must match the note
   under the opposite display orientation. Original table/JSON hashes, source
   identity, money-column ordinals, units and exact source-period keys are bound.
   A note's observed before-tax profit, if present, must also corroborate the
   primary statement. Conflicting populations cannot pass on tax magnitude alone.
4. Every emitted mapping retains its original numeric coefficient, source text,
   blank state and source reference. The final current + deferred = root check
   records explicit comparison-only orientations and raw operands separately;
   it neither flips output values nor changes either source presentation.
5. The root-control comparison can reuse only an independently proven non-root
   overlap from that same original source table and the same primary bridge.
   The final closure authenticates the merge receipt and exact final mapping axis.
6. Query replay rebuilds this proof from original selected JSON. Rehashing a
   forged query/receipt does not replace source evidence. Missing/duplicate profit
   anchors, wrong periods, blanks, arithmetic conflicts and missing independent
   overlap remain fail-closed. The original no-context sign-inversion fixture
   remains UNRESOLVED.

The printed profit equation only corroborates an existing source presentation.
It is not used to select a competing candidate, infer a unit, backsolve an amount
or invent an absent deferred/root operand. Missing roles remain missing.

## Verified gates

| Gate | Result | SHA-256 |
| --- | --- | --- |
| Python 3.12 focused suite | PASS: 429 tests, 0 failures/errors/skips, actual checkout imports, unchanged inputs | `dee301be314a7e8559da01c4da816c997f23674903257fb4a100f33af675466c` |
| 34-document diagnostic | 20 READY / 14 UNRESOLVED, 128 mappings, 2,170 original pages | `27ce7fb1fb18b7d081a01e4360cf085d45901fbde75c4964716de551326c485a` |
| Independent SQLite source replay of that panel | PASS: indexed evidence and complete trials exactly equal, no cache | `8fd4929c3d1426730012b2f28eb05caa42ee0a39781855ce5cdc217f2187f589` |
| Source-observation contract | PASS: no violations | Bound in diagnostic and replay receipts |
| Frozen shared hashes | PASS: original migration pins | Unchanged |
| Ruff and `git diff --check` | PASS | Current owned files |

External artifacts:

- `/srv/bctc-receipts/f39-signed-focused-3d3c9a464a5345519bf5f0e265c9e795/F39_IMPLEMENTATION_FOCUSED_RECEIPT.json`
- `/srv/bctc-receipts/f39-signed-panel-7c0e5bf9fc804b43bc394e0279c228fd/income-tax-bounded-diagnostic.json`
- `/srv/bctc-receipts/f39-signed-panel-cold-a6d23f84d75d4065b54e08e1e8a55050/F39_SIGNED_PANEL_INDEPENDENT_SOURCE_REPLAY.json`

The panel includes all 29 previous opposite-sign holds plus ABB 1, BVB 23,
LPB 74, VAB 249 and VBB 259. Existing READY cases 1/23/249 retain their exact
mapping counts (6/8/6); none regressed. Seventeen sign-held documents are now
READY: 27, 30, 39, 40, 44, 45, 70, 72, 142, 143, 167, 168, 187, 260, 261, 262, 264.
No previously mapped note detail was dropped to gain this result.

## Remaining work and acceptance boundary

Twelve opposite-sign holds remain: 54, 56, 57, 64, 65, 66, 180, 181, 185, 186,
193 and 231. These are **algorithm/evidence gaps, not sealed genuine conflicts**.
Read-only inspection identifies incompatible representations of period headers
(relative current/comparative versus explicit year/end date) in the six KLB and
four SSB cases. Do not equate those keys or guess dates from filenames/amounts.
STB 193 also prints an explicit carry-forward annotation on its before-tax row;
the current exact bridge-label allowlist does not accept that annotation yet.
Inspect and authenticate the missing context, including TPB 231, before acceptance.

LPB 74 and VBB 259 remain on their parent-semantic holds. The previous exact-alias
proposal is still not adopted; source population and the ABB regression must be
reviewed together. Other non-sign groups from the 71-document full271 backlog
remain unchanged and require their own source audit.

This bounded diagnostic does **not** replace full271/common204 accounting,
fresh SQLite persistence/reload, full PDF/residual audit, projection or family
release ledger. Do not extrapolate 217 READY / 54 UNRESOLVED as a completed full271
result. The last complete experimental run remains 200/71 on preceding bytes.
F39 is not terminal; no READY_FOR_INTEGRATION, F36/F37 work or F41 is authorized
by this checkpoint. The ultimate PDF-to-schema Excel objective remains open.
