# F39 same-source accounting-period checkpoint 2026-10-21

Non-terminal F39 implementation checkpoint, **not family acceptance**. Parent
`bb47c19af97bbd639a65142d5302a4d5ccc33f71`; own branch
`codex/f39-income-tax-laptop`; migration ancestor
`8efd618b6c77f0cdbb402a440e7ba3b3549184f1`. Full goal remains bank reports
2025-current and all remaining families, ultimately accurate schema/template
Excel.2024 source PDFs remain outside production/provider queues; printed
comparatives inside in-scope PDFs are retained evidence.

Only F39 evaluator/tests changed. No provider, re-extraction, accepted-result
persistence, source PDF/SQLite/JSON overwrite, old-artifact cleanup,
F36/F37/F41 changes or common-branch push. Both shared files remain frozen.

## Implemented source-local period parsing

- Literal `ky ke toan` duration clauses now parse alongside existing `ky` and
  `ky hoat dong`. Existing independently printed header endpoints, month
  lengths, scope, source identity and all accounting checks still apply.
- A new same-day reference binds only the one date printed in the **same
  complete NOTE caption**: `vao ngay DATE va cho ... ket thuc cung ngay`.
  It requires the finite explicit RIENG/HOP NHAT report scaffold, with an
  annual financial-year or interim numbered-month clause. It cannot borrow
  a date from another title, narrative, table, page or filename.
- The only optional trailing furniture is the reviewed pair of numbered
  fiscal-obligation and tax headings. Parent/child outline numbers must join;
  they are not hardcoded to a bank, page or note number. Unknown headings,
  additional dates/assertions or unmatched remainder HOLD.
- Raw full caption, source lines including whitespace/empty lines, date
  antecedent, scope text and recognized furniture are retained. Real and
  literal newlines, and composed/decomposed Vietnamese, are supported without
  changing source text. No start date or missing monetary value is invented.
- Unknown footnote markers cannot disappear under normalization. Superscript
  digits, stars/daggers, punctuation-only lines, unmatched/nested parentheses
  and unreviewed parentheticals HOLD before caption/furniture normalization.
  Historical/signing narratives retain the existing start-anchored treatment;
  a historical same-day phrase is not promoted to a current-period assertion.
- Before an owned caption is trimmed to its first `cho` clause, earlier finite
  affirmative annual-ended, duration-ended, quarter/year, date-range or
  recognized statement-caption annual-year assertions are detected. They
  cannot silently disappear so the convenient final assertion wins.
- New form furniture `B04a/TCTD-HN` must be an exact raw terminal literal;
  punctuation impostors or trailing prose/dates are not stripped. It remains
  visible in its constraint. This is not a generic form-code allowlist.

Independent bounded source review and adversarial code review PASS. The
legacy caption-furniture paths still require review before whole-family
release; this checkpoint makes no universal parser-completeness claim.

## Final-byte verification

Python3.12.3, `-B`, fresh isolated bytecode prefix: **917/917 focused tests
PASS**,0 failures/errors/skips,295.00s,42 actual checkout imports.76 cases
were added to841, including source-local binding, misleading prefixes,
historical prose, raw markers, generic outline numbers, whitespace/NFD and
fully self-resealed query/inventory tampering. Source/config/test bytes,
HEAD and worktree status stayed unchanged during the witnessed run. Ruff and
`git diff --check` PASS.

Final evaluator SHA:
`ec058002739c1cb5eece1f4c0b62bfef6bad60cbbb3042de311deaac5ed034c7`.

Signed-display tests SHA:
`c9d757de4c37c0755342d16121c15444948d11d01a6c890ed1efdc91784394ac`.

Shared evaluator SHA:
`bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`.

Shared runner SHA:
`d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.

Focused receipt:
`/srv/bctc-receipts/f39-same-day-focused-1792583739988-dc75cd9539e67/F39_IMPLEMENTATION_FOCUSED_RECEIPT.json`

SHA `dbc6fb88c2238fa92d26bd99c5f074639c4bbd6623fa23e183e19cffd8d5c27f`.

Original-SQLite34 diagnostic: **12 READY proposals /22 algorithm holds /59
mappings**, versus parent's9/25/50. Only260/261/262 gain READY, with exactly
three observed mappings each: PBT5728, prior-tax adjustment5733, current-tax
expense5723. The existing forward GROUP/business/transfer/current controls
remain mandatory and PASS. Their declared unit remains MILLION_VND; printed
prior dashes remain DASH_ZERO with exact lexical evidence, including262's
leading space. No RATE or tax-effect adjustment is re-exported as income.

Every previous9 READY observation retains exactly the same role/RNID/unit,
typed values and original source references. No previous proposal is lost.
These are proposals, not accepted workbook output.

Diagnostic:
`/srv/bctc-receipts/f39-same-day-panel-1792584145580-50c03e5d03881/income-tax-bounded-diagnostic.json`

SHA `cfe806fddb63724346bc6f976b3cff6d3042e87f2eafda15746cb23821e5baf8`;
23655304 bytes. Source-observation contract PASS,0 violations. Nested audit
412 mappings/824 cells/2 derived cells/6 source blanks/6 partial mappings is
not the59 proposed export mappings.2170 source payloads were read:2169 exact
plus the existing lossless EIB TEXT-label witness;10196448 bytes,34 SQL loader
calls,0 base-cache hits. Load2.897s/base38.042s/family119.164s are measured
timings, not a speedup claim.

Independent cold original-SQLite query/trial replay and semantic export
invariants PASS with exact typed equality. Source/config/test/database bytes
remain unchanged; no cached proposal becomes acceptance authority.

Cold receipt:
`/srv/bctc-receipts/f39-same-day-cold-1792584503538-7c82a019b530d8/F39_SCHEMA_SEMANTIC_INDEPENDENT_SOURCE_REPLAY.json`

SHA `944b4389f316f70ede71a2b5df56ca3c4bd2aa9e70d15f9a68ddca093199dbbb`.

## Read-only KLB66 PDF discrepancy review

PDF skill used for a complete-page visual comparison, not OCR or extraction.
The restored original source PDF has SHA
`91a030b2dcf82adee0ef5db4ef924f24287d08d72e9ec16ee116e5539c2c0f50`,
11588444 bytes. Its physical pages9 and10 both visibly print QUY II NAM2026.
Original selected page10 JSON instead stores section title QUY II NAM2020;
its table title is null. Thus the observed discrepancy is a stored Gemini
JSON caption transcription error, not a claim of damaged restored artifacts.
The page10's **own** visible caption is authority; no year is inferred from
the filename or adjacent page.

Original JSON VID:
`gfpstorev1:json:bb240ceb453ad7b8609e5ea1cef271963c20353ee25bac604d94f76f7c407aca`.

Original canonical payload SHA:
`df5109476cd9e4fcd2d4cca9426adb697c0437f1ce9325f960836dd55518e97e`.

Complete pages rendered with Poppler24.02.0 at200dpi; both1654x2339. PNGs:

- `/srv/bctc-receipts/f39-klb66-cf-visual-i2xyixpt/tmp/pdfs/klb-full271-066-cf-physical-09.png`
  SHA `f08c510114d256cd33513e9f63e62a2d0e1ef9a3f13b3ba114d1e2bccc2fdc94`.
- `/srv/bctc-receipts/f39-klb66-cf-visual-i2xyixpt/tmp/pdfs/klb-full271-066-cf-physical-10.png`
  SHA `49b19f829805160ccda342e9666a6a3902d59ff90b62f6a286d6ac7d4ecdf1ea`.

External additive review receipt SHA:
`a6c883daaf1634d2659683670478bf1d2997ff3dd87c7e9b59b8511a9dacbfe2`.
Path:
`D:/bctc_bank/restore-receipts/F39_KLB_066_CF_CAPTION_VISUAL_REVIEW_2026-10-21_1792584474577.json`.
It binds full source/selected JSON and image identities; the additive
publication receipt records exact S3 versions after publication.

**No caption repair has been registered/applied.** The original thirteen
repairs/render registry remain unchanged, and66 remains held. The current
repair API cannot represent a title correction; a separately reviewed
family-local caption-repair axis, deterministic full/crop pixel verification,
restore-version linkage and fresh public/cold rebuild are required. Correcting
the caption alone must not waive the independent comparative-period,
continuation, unit, scope or accounting gates.

## Next work and release boundary

Next structural route is the actual recognition GROUP in181/185/186/187.
Preserve printed scope when removing only authenticated structural ancestry;
the observed-zero deferred-income row is not authority for a nonzero additive
expense rule.187's literal root `(*)` joins its unique owned estimation
narrative and must remain visible.180 has no actual GROUP and stays separate.

The remaining22 are algorithm/evidence holds, not terminal genuine-U seals.
No current full271/common204 release, final results persistence/reload,
whole-PDF visible/residual audit or final family seal is claimed. The six
migration blockers have implementation/regression coverage, but authoritative
whole-family release still requires independent exact271/204 corpora, source
frontiers, source-only/N/U dispositions, database integrity and release ledger.
The frozen generic runner's historical140-document release constants are not
authority for271/204. A family-local release wrapper/audit validator remains
necessary; proposal READY and JSON export are not canonical/Excel authority.
The accepted-result-to1955-item-template bridge and all remaining families
remain part of the active final objective.

Mutation coordination gate:
`bctc-ai/coordination/2025-current/v1/events/20261021T114031024901Z-LAPTOP_INTEGRATOR-HEARTBEAT-f3f312a21ca04412b78f570aa036be2c.json`

VersionId `hDfWxn33i9frOs.exnScnCSmdpEv_lB0`, SHA
`e2157f9039388f48e994915eb72400e406500ab9450e7df9fa6bc7b329ab9b1c`.
