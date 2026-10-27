# F25 source total and local period lanes — source draft, UNRUN

Base: `e890c6ba844c8e4a524a18639f13cb86be9c0da5`, owned branch
`codex/f25-source-total-lanes-v1`. No test/lint/import/compile, corpus/SQLite,
PDF render, provider, WSL, commit, selection or financial acceptance occurred.
Root owns any later synthetic test execution and actual source pilot.

The frozen multitable evaluator and generic runner remain unchanged:
`bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2` and
`d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.
Before editing, the F25 runner was
`7d4b3617ec9e8f422c129b9cbe1a2bc04cf39a513aa41711da32719c9683a4c1`,
and the F25 adapter was
`dec79041546f909c3206b081f201b505cc3aa952228a119c7d9f6af26792247a`.
They matched the committed e890 source. New producer bytes require new source
capture and validation; historical stores are not relabeled.

## Approved observations and authenticated input

Owner0475 and the review receipt identify three F25 defects. Receipt
`restore-receipts/FOCUS_FAMILY_PDF_REVIEW_FULL271_20261027_V1.json` has SHA
`47fe733e3e957027a2e450257bc30649dd0ae4a72ef0cc8a00f3d3c90e6714a5`;
its F25 mapping manifest has SHA
`4e2d97a8106209789b91db13fc46d62ae246fd91f469af5d5730fcb3b5abc027`.

- LPB69/p53: observed CD net subtotal36,253,023/35,022,586 and bond net
  subtotal27,843,990/20,436,330 already include their discounts. The printed
  bottom total is64,097,013/55,458,916. The old root64,067,758/55,427,793
  includes those discounts a second time. ImageSHA
  `2d74dab23053a991f5d117c111c28359c2833f062285ef9318ec43e96aa38723`.
- MSB76/p47: a current-only maturity table's one-column source references
  accompany a two-cell parent/root mapping from the neighbouring summary.
- VAB241/p38: current-only detail/net-value references accompany comparative
  values from p37, including an equal-value bond comparative that cannot be
  authenticated by numeric coincidence.

PDF source SHAs, respectively:
`d3cf5756961841199cb971f494d7579c05095964284b6dc82a45dafbc563fab7`,
`0fef0b3df6d3453b4532fd56de24f428f3ced958cebc88b1befd43924b73ed42`,
`925bc21f1378480890477dd3d4b54208b597c8865c752cdabd0b05206ad6d7b0`.
These identities and numbers are review evidence only. No production route
tests a bank, ordinal, filename, page number or target amount.

Owner0477 supplied `restore-receipts/F5_SOURCE_PACKETS_20261027_V1` for all
three cases. Its approved LPB53/MSB47/VAB38 PNGs were inspected. Packet refs
and complete persisted candidates, including their actual component regions
and region query receipts, are retained in the fixture manifest. No separate
cluster or query evidence was invented/regenerated. The four original page
JSON files were copied byte-for-byte and checked against each packet's stored
canonical page SHA and size. Their fixture manifest SHA is
`627e64289e583b007763a6d4fc9a79e4238d5c85449cde03a7310dba801a325e`.
It resides under
`tests/fixtures/source_structure/f25-source-total-lanes-20261027-v1`.

All three packet producer axes bind old runner7d4b3617…, adapterdec79041…,
the frozen shared pins, run
`gjfafstorev1:run:405b665e1dcf485edcb977e4c4e6e267fc2ccbf4fef103708848fb4ed8fab3b7`
and implementation axis
`693b6ad47b696c2af288d451f113b0985f74bd22e65c6e822a221afb167497a5`.
The packets do not turn a changed producer into that old run's accepted source.
No financial values or row shapes were guessed; no repair registry was edited.

## Printed total from the closed net frontier

The LPB source actually contains raw r11 `TOTAL`, null label and hierarchy
`[null]`, with the printed two-period values. The old candidate already has
the exact local equation
`gjfoltiev1:equation:c49f332febbfcd854e735db5db7a52c7b2cdee25d05283a71ea03739d9da7890`:
`EXACT_CLOSED_STRUCTURAL_GROUP_SUBTOTALS_EQUAL_TERMINAL_TOTAL`. It proves
raw r5+r10=r11 correctly. A later global root derivation adds the declared
validation-only `GENERIC_ISSUED_PAPER_SOURCE` discount rows again.

The family-local binder selects that unique structural local equation and
its actual raw terminal result. It requires fresh classification/explicit
owner equality; complete original local date/column and unit proof; exact raw
SUBTOTAL/TOTAL identities; complete component refs joining distinct mapped net
parents; observed integer/dash cells; and exact arithmetic as a veto. Amounts
never select or retarget a source row. Net parent mappings remain unchanged.

The family root now references raw r11 and its two original cells. The old
global derived root, global root equation and complete old root permissions
remain explicitly superseded in a deterministic adapter receipt. The unrelated
local equations stay active; the new root permission points to the retained
local equation. The retired global root equation/permissions are removed from
the active closure on success and HOLD, preventing dangling root authority.
On failed source/population/unit/lane/complete-proof checks, every mapping is
withheld with its before-image and the candidate remains `UNRESOLVED`.

Retired and withheld mapping before-images use lossless canonical JSON UTF8
text plus SHA256 and byte size. Active mappings and their source references
remain ordinary structured objects. This distinction is necessary because the
unchanged source-observation contract walks every nested mapping-shaped dict;
an evidence copy must not count as a second emitted mapping or resurrect a held
financial value. Tests decode the exact before-images, audit the full candidate
including all closure evidence (READY count equals emitted mappings, HOLD
count0), and require fresh replay to reject malformed/tampered envelopes.

## Authored lane guard

Frozen global role reconciliation merges current/comparative observations and
unions record-level source references. This can attach a two-cell global
mapping to a source row that has only one selected money column. The family
adapter now checks source widths after restoring original source references
and before the candidate is sealed/published.

A width mismatch makes the whole candidate `UNRESOLVED`, empties its mapping
axis, marks structural-root emission false, and adds a deterministic receipt
with withheld mappings, exact source refs and row before-images. It changes no
raw page, cell, sign, unit or mapped financial value. The family replay validator
recomputes this same guard from source and rejects receipt/candidate drift.

A table with one current column may keep one current value. A two-column row
may keep both locally observed lanes. A mixed summary/detail width cannot
borrow the missing lane. Separately dated one-column tables also remain HOLD:
dates, equal amounts and a common role do not authenticate matching economic
population, maturity qualifiers, non-date headers or owner/continuation scope.
No new cross-table join is authorized by this draft.

## Source tests and outstanding gates

New focused module:
`tests/unit/test_gemini_json_issued_valuable_papers_source_total_lanes_v1.py`.
It contains compiled-family/coalesced public evaluation and replay contexts
for the ordinary positive and current-only maturity/summary negative, plus
isolated guard tests for net columns, equal-value comparatives, single-lane
positives, reversed-source ordering and unsupported separate-table joins.
It also contains exact packet-context LPB printed-root/net-parent/equation/
retirement checks and exact MSB/VAB HOLD/replay checks. Negative controls cover
duplicated raw total, ambiguous local equation, wrong unit/lane/owner/raw row,
and deliberately resealed malicious partial or validation-child proofs.
Source pages stay unchanged and held/retired receipt tampering must fail replay.
All checks are **UNRUN**; source-ready is not a completed runtime validation,
corpus pilot, new store or financial acceptance claim.

Root must capture final source/config/test hashes, run the synthetic family
and source-observation gates in a fresh pinned source tree, review all failures,
then authorize any bounded real-source pilot. Preserve positive family cases,
typed blanks, raw signs, source-local units and qualifiers. No blank-to-zero,
equation backsolve, magnitude unit inference or historical acceptance rewrite.
