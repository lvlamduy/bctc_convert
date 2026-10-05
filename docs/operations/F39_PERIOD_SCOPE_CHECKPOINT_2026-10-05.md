# F39 PERIOD/source-population checkpoint — 2026-10-05

Status: verified implementation checkpoint, **not family acceptance**.
LAPTOP_INTEGRATOR owns F39 only. Branch `codex/f39-income-tax-laptop`;
parent `a0ac7f8940c307f9c11a4609ec476766bbf09a35`, migration ancestor
`8efd618b6c77f0cdbb402a440e7ba3b3549184f1`. The common branch remains at
that migration ancestor. No F36/F37/F41 changes, provider calls, PDF
re-extraction, source-database writes, or artifact cleanup were performed.
Production scope remains reports dated 2025 onward; printed 2024 comparative
columns inside those reports are not 2024 production documents.

## Source semantics and ownership

`CURRENT_PERIOD_TAX_EXPENSE_SOURCE_ONLY` is monetary validation-only and has
no schema binding. RNID5724 remains exclusively printed `Năm hiện hành`.
PERIOD and YEAR have separate presentation/equation names. Both require an
actual blank GROUP, exact descendant paths, complete supported components,
and the first source-visible closing subtotal/total. Named closing parents
must have the exact proven group/self path; foreign/unknown ancestors veto.
Anonymous `[original_group, null]` closures retain their original source path.
Arithmetic never establishes ownership or identifies an unknown component.

The underprovision phrase `Dự phòng thiếu trong những năm trước` is accepted
only inside that authenticated current-expense frontier, not as a global
PRIOR alias. YEAR/PERIOD operands and their closing parent must be explicitly
numeric source strings. A dash/blank cannot become zero even if the other
printed operands make an equation close. RATE adjustments cannot acquire
YEAR/PERIOD roles or income-basis schema targets.

Source context now binds the full typed primary-caption inventory and
single-table, exact affirmative recognition narratives. A unique report
scope may be inherited only from at least two distinct actual statement
types, with no contradictory caption; the actual enum is `CASH_FLOW`, not
`CASH_FLOW_STATEMENT`. Bare table-caption conflicts, negation, and entity
overrides cannot disappear from the inventory. Exact matching explicit
parent-entity populations remain supported; they are not broadened to the
whole consolidated report. Multiple-table narratives do not lend authority
to an unrelated table. Signed-display and final source controls use this
same independently rebuilt scope evidence.

Final checks inspect raw YEAR/PERIOD populations even when the component is
validation-only or its mappings were suppressed. Correspondence binds
original money-column axes, source period keys, and printed duration lengths
from headers or owned captions. Endpoint-only dates require printed duration;
relative current/prior labels alone are insufficient. Bare years cannot
annualize YTD/quarter captions. Unsupported written month lengths and a
printed month length inconsistent with an explicit date range fail closed.
No missing start date is generated. The note-only population route remains
an explicit algorithm hold until an independent counterpart proof exists.

## Additive correction to earlier F39 source analysis

The previous checkpoint's interpretation of ABB full271 ordinal1 as a flat
YEAR presentation was incorrect. This is an analysis correction, not an
artifact or migration-pin correction; no historical document is overwritten.

Original ABB p66/s2/t1 has exactly one table, a real blank GROUP
`Chi phí thuế TNDN hiện hành`, child `Kỳ hiện hành`291.335/104.082,
underprovision112/403, and anonymous SUBTOTAL291.447/104.485 with path
`[GROUP, null]`. Its owned narrative is
`(a) Ghi nhận trong báo cáo kết quả hoạt động hợp nhất`, and columns explicitly
state six-month periods ending 30/6/2025 and 30/6/2024. Page version is
`gfpstorev1:json:90f2b0b298f8a83191cb27ab12108aaedb62e6f30b53d0beaf3ed388a88ddc96`;
table SHA `92a5abfe6694b0d517e1deb60cea8a817def6b53c5f6c89cbc31c234dd74cd2b`.
The component must never be RNID5724. Latest PRIMARY descriptor correctly
selects p10 CURRENT r18, DEFERRED r19, and printed ROOT r20; column2 is
footnote35, not money. The independent RATE table p67 remains a separate
population, not another operand of the p66 PERIOD equation.

## Exact verification evidence

All tests ran on Linux Python3.12.3, `-B`, with a fresh isolated bytecode
prefix. Checkout imports and source/config/test bytes were verified unchanged
through each final execution. The early 532-test run had six failures and is
retained; it is not acceptance evidence. Intermediate PASS runs538/546/549
are also retained, but only the final bytes below support this checkpoint.

- Final focused: **553/553 PASS**, zero failures/errors/skips,42 actual
  checkout imports,118.17s. Receipt:
  `/srv/bctc-receipts/f39-period-scope-focused-1791128249362-0ba0c8473048c8/F39_IMPLEMENTATION_FOCUSED_RECEIPT.json`;
  SHA `dd6fc755fddc4490d16765f23db3d6e739b50e3ba5b718ebdf127129a87e4198`.
- Original-source 34-document diagnostic: **15 READY proposals /19 algorithm
  holds /96 mappings**, source-observation violations0. Read2170 selected
  original SQLite page payloads:2169 byte-exact plus the retained lossless
  EIB redundant TEXT-label witness, with all original cells/ordinals retained.
  No results persistence or corpus acceptance was performed. Receipt:
  `/srv/bctc-receipts/f39-period-scope-panel-1791128440995-49e349da49a2d/income-tax-bounded-diagnostic.json`;
  SHA `62644c8ca1cd0a36a399f595dbdcf5446fa438bcbb5d04aa405e58cf6d75d3ae`.
- Independent cold SQLite query/trial replay: exact complete trial equality
  and schema-export invariants **PASS**, not family acceptance. Receipt:
  `/srv/bctc-receipts/f39-period-scope-cold-1791159788454-c44899cd57b4f/F39_SCHEMA_SEMANTIC_INDEPENDENT_SOURCE_REPLAY.json`;
  SHA `6542199e6400bc98cfcfadb71834b9638b5531fa2dd1334a6225a62e38290b95`.

Full271 ordinal axis:
`1,23,27,30,39,40,44,45,54,56,57,64,65,66,70,72,74,142,143,167,168,180,181,185,186,187,193,231,249,259,260,261,262,264`.
Diagnostic trial ordinals are renumbered; comparison uses this full axis and
source SHA, never the trial ordinal alone. Metrics match the immediately
preceding semantic checkpoint, not the older unsafe 20-READY baseline.
ABB1 now advances from the incomplete-singleton hold to the unresolved RATE
measurement-basis hold; STB193 likewise has authenticated scope but remains
held on RATE measurement basis. These are unfinished algorithms, not
genuine-source-conflict terminal seals.

Implementation SHA pins:

- F39 module `6f253404c87e3c2e24de875639b46d4d5a4697a2860b80f3e5e83a4ff2c4c10a`.
- Topology `bd75ad7650c16bf583e7a996aeedfd76fe384b85019629d7a408f44cbbe11bcc`.
- Evaluation `cedfd19b9b1b348a4acb9e818684a7ef136bdf46b7664d5d44abc80115cf18ab`.
- Schema binding unchanged `ec5765e3ea8dc3628641b71df8ea509241951e7b68d506a5c0622b6cb0bca7b8`.
- Frozen evaluator unchanged `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`.
- Frozen runner unchanged `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.

## Required continuation

Re-evaluate original RATE tables under separately authenticated private
measurement-basis specs/query receipts, before generic consumed-row filters.
Preserve genuine printed PBT, current/prior tax, independent INCOME/YEAR/PERIOD
and deferred/root populations; do not merely delete unsafe mappings from an
old candidate or fabricate a PRIMARY descriptor. Genuine INCOME scopes must
retain their ordered projection policy. VBB260/261/262/264 have no printed
TAXABLE_INCOME terminal in the inspected RATE frontiers; their tax-effect
adjustments do not prove income-basis5730. Original full rows and unknown or
blank residuals require explicit disposition or an algorithm hold.

Four SSB period-correspondence holds, SSB187 recognition GROUP with blank
deferred, KLB relative-period ambiguity and other residuals remain open.
Current-code authoritative full271/common204, persistence/source replay,
observation contract, SQLite integrity, PDF/residual audit and release ledger
are still required before F39 terminal status. Only then continue F36→F37;
do not open F41 yet. Publish final witnesses under new immutable S3 keys with
exact VersionId readback; use HEARTBEAT, not READY_FOR_INTEGRATION, for this
nonterminal checkpoint. Never push the common branch directly.
