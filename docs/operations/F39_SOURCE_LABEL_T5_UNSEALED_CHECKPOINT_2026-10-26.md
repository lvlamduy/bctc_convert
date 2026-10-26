# F39 T5 source-label HOLD: unsealed checkpoint

Status: UNSEALED. No financial acceptance, integration promotion, or F41 opening.
Scope remains bank reports from 2025 to the present. Source comparative 2024
columns are preserved; standalone 2024 reports remain outside production.

## Source finding and behavior

Coordinator assignments 0428/0429 approve a negative source observation for the
NVB/NCB parent-company Q1 2025 PDF. The selected JSON calls physical page 6,
s1/t1/r17 deferred tax, while the independently reviewed printed row is the
total income-tax expense. This is a label substitution on a printed total row,
not an extra phantom row or proof that the PDF has a text layer.

The committed registry binds PDF SHA-256
`82d67a1543618eb9b59e1cdc819049e54dcc35eeace90a5b745d77f03ed8940f`,
selected VID
`gfpstorev1:json:860d1b7f024750929d3880fa06c13f62b1c074baecb463847a07a0bd5b8dbb7a`,
physical page 6, s1/t1/r17, original label/hierarchy/kind, and money columns
4/5. Its fixed file SHA-256 is
`c8788461c2e3aed5068c9ba3c329f39bfd13d2cf8dea7aede724bbff6b017bcf`.
The review reference and source-identity reference are also pinned in that file.

If a READY candidate cites that row as DEFERRED_TAX_NET, the family withholds
all its mappings with `SOURCE_TRANSCRIPTION_DISCREPANCY`. It retains the original
candidate, source references, raw cells and authenticated context in the HOLD
evidence. No financial cell, label, sign, unit, role, or period is repaired or
backsolved. The rule does not depend on a global document ordinal, zero/dash
values, or arithmetic. An unrelated source receives no new context field.

The selected PRIMARY source is bound through the document income-statement
period inventory, not the notes-only population inventory. Its runtime page,
section, table, row, and actual YTD column axis are included in the proof.
A different selected VID on this PDF/page requires a separately reviewed
profile and fails closed instead of borrowing the old observation.

## Authentication

The runner independently authenticates the original PDF bytes and a new
pdftoppm render at 100 DPI on both warm and cold passes. The registered RGB PNG
is 828 by 1170, 478720 bytes, SHA-256
`3904383fb763660e06aebc9858a5168589584b0013b6e7d4bfb9ef77e0478917`.
The entire ordered per-document admission vector, including empty slots, must
match between passes. Missing applicable warm evidence, drift, incomplete or
reordered vectors stop replay. The final source/implementation barriers remain
in place. Both bounded and full audit outputs retain the admission vector.

The family operation's exit frontier now includes the new module and registry:
17 exact file references. Existing hash checks remain intact and every listed
file has a drift control. The two frozen shared source files are unchanged.

An external promoter or validator using the cold adapter must pass
`expected_source_label_discrepancy_axis` from the complete warm audit. Its
default `None` grants no authority for an applicable profile. The actual runner
already passes the vector.

Claude message 0436 reports a read-only join verifying the same exact page-6
VID and canonical JSON SHA in FULL271 and COMMON204. Other pages of this PDF
have different manifest frontiers; those are not conflated. No second T5
profile was guessed or added.

## Validation record

Runtime base is `c0e85a59f68b5b91982ec70d2a4bdfe3ec5929b1`.
Current code/test checkpoint is
`53b6b16a6818b5f71ccb7285e55ed730c4ae14ae` on
`codex/f39-t5-source-label-hold`.

Every job uses a fresh clean Linux clone, Python 3.12.3, a 2 GiB address-space
cap, nice 19, and the coordinator's one-test-job lease. Run receipts and logs
are retained under
`D:\bctc_bank\restore-receipts\CODEX_F39_T5_TESTS_20261026_V1\`.

- Focused V1 stopped at one Ruff import-formatting error; pytest did not run.
- Focused V2 at `dd70916d`: Ruff PASS, 71 tests PASS.
- Nonlegacy V1 at `dd70916d`: interrupted after the exact dependency-frontier
  assertion failed because it retained the 15-file list. Partial result:
  1 failed, 2058 passed, 73 subtests passed. It is not a full PASS.
- Focused V3 at `53b6b16a`: Ruff PASS, 98 passed, 164 deselected. This includes
  the expanded exact-file/drift controls and nine synthetic runner-vector
  controls. The latter exercise real synthetic source replay but substitute
  an explicitly labelled I/O admission callback; they claim no real PDF proof.
- Nonlegacy V2 at `53b6b16a`: Ruff PASS, all 28 selected modules completed:
  **2889 passed, 123 subtests passed**, zero failures/errors, in 1503.43 seconds.
  Receipt SHA-256:
  `7acbb5d786678af256db1847f2276031b5c180069c42e4fc607680e11188386a`.
  The receipt identifies the exact source/test bytes, import origins, resource
  limits, frozen source hashes, JUnit and runner scripts. Native receipt/log
  bundle: `f39-t5-nonlegacy-20261026-v2/` under the receipt directory above.

Independent static review of the final runtime/test delta found no material
finding in its stated scope. Its external receipt
`CODEX_F39_T5_STATIC_REVIEW_20261026_V1.json` has SHA-256
`2146487eaa4163c481438b33d0bb2cf681a9a995a7046f9b32b9e38e56501c8d`.
That review originally saw this document with the full run pending; this
documentation-only update records the now-closed root-owned test result.

The full authorized nonlegacy gate selects 28 modules: 27 existing modules plus
the new T5 controls. Two legacy 8-bank calibration modules requiring absent
historical data are explicitly excluded per coordinator assignment:
`test_build_income_tax_8bank_codex_verified_mapping_v1.py` and
`test_build_annual_2025_income_tax_8bank_codex_verified_mapping_v1.py`.
No provider, extraction, actual corpus, real-PDF, or results-store job is run
by Codex under this test lease. Synthetic unit fixtures are not corpus evidence.

## Remaining coordinator gates

After code review and the complete synthetic gate, Claude owns real source
pilots 110/225 with controls 20/39/231, then authoritative FULL271/COMMON204,
independent source replay, observation contract, SQLite integrity, source PDF
and residual audits, and the family ledger. Expected pilot behavior is a
source-discrepancy HOLD with no mappings for 110; 225 stays at its T4 HOLD;
controls must remain unchanged. These are expectations, not observed results.

F39, F36, and F37 remain unsealed until their respective complete gates close.
The new branch must not be pushed directly to the integration branch. No old
artifact or S3 object is deleted, overwritten, or relabelled by this checkpoint.
