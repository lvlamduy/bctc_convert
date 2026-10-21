# F39 document-annual and forward-accounting checkpoint 2026-10-21

Non-terminal implementation checkpoint, **not family acceptance**. Parent
`0e666b7dfdf84f43bbda3f1a88c94ec8fbc757f0`; own branch
`codex/f39-income-tax-laptop`; migration ancestor
`8efd618b6c77f0cdbb402a440e7ba3b3549184f1`. Only F39 code/tests changed.
The goal remains all remaining bank reports from 2025-current and all remaining
families, ultimately authenticated PDF-to-schema/template Excel. Printed 2024
comparatives inside in-scope reports are evidence, not permission to queue
2024 PDFs. No provider calls, re-extraction, source/database mutation,
accepted-result persistence, cleanup, F36/F37/F41 changes or common-branch push.

## Authenticated document-annual inheritance

- A fresh document receipt requires caption-authenticated INCOME_STATEMENT
  **and** CASH_FLOW sources. Every discovered continuation must independently
  own the same annual context, relative-year pair and explicit report scope.
  Conflicting or unresolved sources cannot be discarded by majority vote.
- A positively tax-owned NOTE with the literal two-money `Nam nay/Nam truoc`
  pair may inherit that explicit receipt. This is separately identified as
  `INHERITED_AUTHENTICATED_DOCUMENT_ANNUAL_PERIOD`, not printed absolute NOTE
  years. The comparative-year derivation remains explicitly typed.
- Local captions, selected headers, owned single-table narratives and actual
  ancestors are exhaustively retained and checked for period/entity conflicts.
  Quarter/month/interim/YTD, unsupported affirmative ranges and conflicting
  current years veto inheritance. Historical prose and signing dates are not
  positive period authority. Missing bullet/normalized leaf text is not
  silently treated as an entity ancestor, nor is a true ancestor discarded.
- Generic `Ky nay/Ky truoc` does not acquire previous-year authority. No raw
  keys, amounts or units change; no start date is fabricated. Public replay
  reconstructs the full inventory and rejects self-resealed invented proof.

## Original business/transfer tax forward control

`original_rate_forward_control_receipts` is additive to the original NOTE
adapter. The original standalone basis receipts, holds and private proofs
remain unchanged. Recognition as an ITEM cannot exempt a business result from
the same accounting check required for a SUBTOTAL.

The finite source grammar selects the unique PBT/rate, numeric increase and
decrease GROUPs with all direct children, business result, separate transfer
income and tax observations, optional printed prior adjustment, and final
current result **before** arithmetic. Full raw rows, typed cells/dashes,
locators, money columns, source/spec hashes, unit/scope and original private
GROUP equations are retained. Unknown, duplicate, interleaved, unobserved or
foreign-ancestor rows HOLD. Increase must be nonnegative and decrease
nonpositive as printed; no sign search is permitted.

The observed forward equations are:

1. Each GROUP equals its complete direct children and has one exact private
   equation proof over those same children.
2. Printed rate + increase GROUP + signed decrease GROUP = business tax.
3. Business tax + observed transfer tax + printed prior adjustment (if present)
   = final current tax.

Transfer **income** is retained but is not a tax operand. Transfer tax is not
derived from an assumed percentage. Its subtotal proof is honestly typed as
an observed nested component of exact current closure, not a derived result.
Only individually matched unproven-total ordinals receive additive completion
proofs. Blank never becomes zero; printed accounting dashes remain DASH_ZERO.

Actual source ordinals260/261/262/264 all pass this control, with zero residuals
in both money lanes. All sixteen GROUP/business/current equations close.
260/261/262 remain held by independent period checks.264 now retains this full
forward proof rather than relying on source-only row retention.

## Verification on final implementation bytes

Python3.12.3, `-B`, fresh isolated bytecode prefix: **841/841 focused tests
PASS**, zero failures/errors/skips,243.55s,42 actual checkout imports.
Source/config/test bytes, HEAD and worktree status were unchanged during the
run. This adds49 annual-inheritance and39 forward-control cases to753.
Ruff and `git diff --check` PASS. Independent bounded code review PASS after
the increase/decrease directional guard was added; adversarial arithmetic
that still closes with the wrong adjustment direction is rejected.

Final implementation SHA-256:

- F39 evaluator: `c5139ff4edf3f1a7a3bc8918c9dff264a84a54ec3197cd855c575633b466d1ed`.
- Family tests: `4e8fe7478db43a839e369ebf1c3d85ac096f9ccbaeb37bb82acf5b88bbecd4ae`.
- Signed-display tests: `35f9f799d6201e7fb38e5c099b84a774c14a5f2cfd8f7f2221e4ee7791227e55`.
- Frozen shared evaluator: `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`.
- Frozen shared runner: `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.

Focused receipt:
`/srv/bctc-receipts/f39-annual-forward-focused-1792581460333-3e0bca690766d/F39_IMPLEMENTATION_FOCUSED_RECEIPT.json`

SHA `f690a9977cabef869854d9a650b31f9bd84e7c417472367b82c1ce03609fedaa`.

Original-SQLite34 bounded diagnostic: **9 READY proposals /25 algorithm holds
/50 mappings**, versus the immediate parent's3/31/17. READY axis:
`1,27,30,39,44,193,231,249,264`. Five annual sources27/30/39/44/249 regain the
same typed economic observations as the older original-NOTE checkpoint;
264 adds three observed mappings with authenticated annual and forward proof.
All34 typed role/RNID/unit/value observations are identical to the annual-only
intermediate diagnostic. Intermediate802-test witnesses are retained, not
promoted as final acceptance. The older20-READY comparison is historical
evidence, not a nondecrease floor.

Diagnostic:
`/srv/bctc-receipts/f39-annual-forward-panel-1792581798189-3d448200494fb/income-tax-bounded-diagnostic.json`

SHA `4293dd1885c71bdb1fe4a5410779af29c3e0c515a5a5f1479fac444412b83b35`;
23677943 bytes. Source observation contract PASS,0 violations; its nested
378 mappings/756 cells/2 derived cells/6 source blanks/6 partial mappings are
not the50 proposed export mappings.2170 original selected payloads were read:
2169 exact plus the existing lossless EIB TEXT-label witness;10196448 payload
bytes,34 SQL loader calls,0 base-cache hits. Measured load3.753s/base43.923s/
family142.878s are timings, not a speedup claim.

Independent cold original-SQLite query/trial replay has exact typed equality
and semantic export invariants PASS. Source/config/test and source database
bytes remain unchanged. No cached proposal is acceptance authority.

Cold receipt:
`/srv/bctc-receipts/f39-annual-forward-cold-1792582144217-f72450a537b/F39_SCHEMA_SEMANTIC_INDEPENDENT_SOURCE_REPLAY.json`

SHA `9fb7b0ad910fb6d7b8d1dcbabec2caf2c78fd1077b4cc6c68f883b59a35ccb2f`.

## Remaining work and release boundary

No full271/common204 acceptance, current results persistence/reload, final
SQLite integrity, PDF/residual release audit or family-terminal seal is
claimed. These remain required on final release bytes. Algorithm holds are
not genuine-U terminal seals; no unverified proposal goes to accepted Excel.

Next finite work, based on read-only source review:

- 260: parse its explicitly printed same-day annual reference, bound to the
  preceding source date.261/262: support literal `ky ke toan` six-month
  assertions and the reviewed form suffix without dropping other text. Their
  remaining failures are period parsing, not conflicting report populations.
- Recognition GROUP sources181/185/186/187: authenticate actual blank GROUP,
  exact children and first standalone root, preserving printed RIENG/HN after
  structural ancestry removal.187 has literal root footnote `(*)`, which must
  be checked before punctuation normalization.180 has no actual GROUP and
  requires a separate authenticated annotation route. Nonzero deferred-income
  semantics must not be silently converted to additive expense.
- 40/45/168: explicit policy clauses name comparative INCOME/CF/corresponding
  notes and six months ended30/06/2024. Prove that original clause and all
  current sources; never infer a year from `Ky truoc`.72/143 additionally lack
  explicit report scope and must not be relabelled RIENG.
- 54/56/57/64/65/66: relative NOTE/CF continuation axes need a distinct ownership
  and comparative-duration proof.66's original CF continuation caption says
 2020 versus its anchor's2026; keep the conflict pending PDF verification.
- 74 has differing prior-adjustment observations despite equal current totals;
  do not merge by total equality.259 has a missing literal CURRENT alias but
  also explicit local RIENG and period evidence requiring independent proof.
 23/70/142/167 retain the previously documented conflicting/missing evidence.

The final PDF-to-Excel objective is still incomplete. Existing family READY
means proposal only; its JSON export is not an Excel release. Read-only review
confirmed the receipt-aware accepted-result bridge to PipelineRecord is
missing, and current template authority has1955 items, not the1593 base.
That future bridge needs separate review, complete provenance and exact
workbook-value verification; obsolete OCR/geometry contracts are not a bypass.

Coordination gate before this forward-control mutation:
`bctc-ai/coordination/2025-current/v1/events/20261021T111123079561Z-LAPTOP_INTEGRATOR-HEARTBEAT-8bca1c3438c641d6becc328cb242be1f.json`

VersionId `uHifmfFcykPQdzRCKr5OBaaW.rp9f_9I`, SHA
`26847c98b054aede63f8f1835a1991ea5fef07489b929cb311766901d22911a0`.
It read all preceding immutable events and bound the exact active F39 claim.
