# Family 24 — entrusted investment risk capital full271 visual audit v1

This ledger seals Family 24 (`ENTRUSTED_INVESTMENT_RISK_CAPITAL`) on the
immutable 2025–2026 corpus. No provider was called. Source PDFs and selected
page JSON were read only. The result is an experimental schema-mapping
proposal, not canonical/export authority.

## Authenticated inputs

- Full271 index:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`
  (422,971 bytes; SHA-256
  `969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`).
- Common204 index:
  `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json`
  (317,566 bytes; SHA-256
  `acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1`).
- Full271 baseline trials: `/dev/shm/f24-full271-baseline-trials.json`
  (1,534,887 bytes; SHA-256
  `47343bb40200491da97f56a78aef7c7e7317a06e974d245f452d3dcc6996de84`).
- Shared multitable evaluator used for both terminal runs: SHA-256
  `e3efa6e21a63217ea6d94cac883ab112abf45da64a39489fad228b0c8e2fd07d`.
  Family 24 did not edit or claim ownership of that shared file.

Historical old8 artifacts are authenticated only as a disjoint safety oracle.
They have zero source-SHA overlap with full271 and are excluded from the
current-corpus conclusion. Comparator: `DISJOINT_EXPANSION`.

## Baseline and terminal results

The initial full271 sweep was 22 READY / 183 NOT_OBSERVED / 66 UNRESOLVED /
48 mappings. The terminal results are:

| Corpus | Documents | READY | NOT_OBSERVED | UNRESOLVED | Mappings |
|---|---:|---:|---:|---:|---:|
| full271 | 271 | 200 | 71 | 0 | 322 |
| common204 | 204 | 145 | 59 | 0 | 230 |
| full-only expansion | 67 | 55 | 12 | 0 | 92 |

All 66 initial U and all 112 false-N documents became READY. The 71 remaining
N documents are individually PDF-audited true absences. Common204's 204 source
SHAs are an exact subset of full271. After removing corpus-relative ordinals
and their content-addressed IDs, all 204 shared trial status, reason, and
mapping projections are equal (zero semantic mismatches).

Full271 run/sweep/audit IDs:

- `gjfafstorev1:run:d9af7e40dbfe550eab2e1ade67a642f14858fa189f0aa35666284b13b2468dc8`
- `gjfafsv1:sweep:4678829b74211d27c1d5944efdb70e9ddb2c8aa038094598253576f14f453f08`
- `geircfav1:audit:9bdebdc6273c164240fc2d836942c3305d1626f94cf1182a2a88b29ba26066b6`

Common204 run/sweep/audit IDs:

- `gjfafstorev1:run:abf5a47a5e596a7af14f86bb70db10fbbad5110c75c9339fb40c502d0f99b8a4`
- `gjfafsv1:sweep:48d0c72edd34e7a4606ddcbf8e9cf243471fbb8893331a4e91309342106c0e39`
- `geircfav1:audit:be6cbeadbc3981c4d4bf595e5e18e0e0a83819d81e1a8af136d336beda8646d3`

## Complete PDF residual gate

Every primary balance-statement page for every final N document was rendered
directly from its source-SHA-bound PDF using PyMuPDF/RGB/1x1/PNG/no-alpha.
Full271 covers 71 documents and 213 pages: EIB 4, LPB 7, MSB 16, PGB 2,
SSB 10, STB 2, TCB 16, VAB 2, VBB 12.

The authenticated row-by-row inventory (source path/SHA/size, physical page,
selected page-JSON ID, render SHA, and content-addressed disposition) is
`config/families/tm-entrusted-investment-risk-capital-pdf-residual-audit-v1.json`.
All 71 dispositions are
`TRUE_NOT_OBSERVED_NO_PDF_VISIBLE_SCHEMA_MAPPABLE_FAMILY24_ROOT`.

The corpus-relative common204 inventory covers 59 documents / 177 pages in
`config/families/tm-entrusted-investment-risk-capital-common204-pdf-residual-audit-v1.json`.
An additional no-JSON-root extraction triage covered 89 documents: 71 are the
confirmed N documents above; 18 have an exact visible primary balance-sheet
root and are READY. No PDF-visible schema-mappable Family 24 row remains N, U,
or source-only.

## Source repairs and semantic controls

The registry contains 54 authenticated exact repairs over 40 source PDFs/pages:
48 PDF-visible dashes omitted by page JSON and six truncated exact labels.
Each binds PDF SHA/size, physical-page render SHA, selected page-JSON ID,
table/row/cell locator, and before/after text. Out-of-corpus receipts are
skipped; an in-scope mismatch fails closed. No repair routes by bank, ordinal,
note number, filename, or value.

Short `Bằng VND` / `Bằng ngoại tệ` labels are accepted only within an explicit
Family 24 owner cluster. The same labels in another liability family are
negative controls and remain NOT_OBSERVED. Source units `VND` and
`MILLION_VND` are both supported without bank/ordinal inference.

Full ordinals 246 and 250 are VAB Q3 company/consolidated notes with visible
current 3,000, blank comparative, and no usable local unit. Each has one unique
explicit primary Family 24 result in `MILLION_VND` on the same period axis.
Recovery requires every observed note-total lane to equal that primary result.
Each maps VND `[3000, null]` and OTHER `[0, null]`; comparative cells remain
typed `BLANK_SOURCE_CELL`. A mismatch or all-blank note cannot recover a unit.

Equations only corroborate/veto observations. Blank/null never becomes numeric
zero because an equation closes. A printed dash maps `DASH_ZERO`; a dash lost
from JSON is usable only through its registered PDF receipt. One blank lane
does not erase the observed lane; an all-blank role is omitted.

## Source-observation contract

| Corpus | Mapping occurrences | Cells | Partial | Source blanks | Derived | Violations |
|---|---:|---:|---:|---:|---:|---:|
| full271 | 644 | 1,288 | 30 | 30 | 60 | 0 |
| common204 | 460 | 920 | 22 | 22 | 48 | 0 |

Occurrence counts include candidate and stored-source replay. Every retained
blank is typed null; no blank-derived numeric mapping passed the gate.

## Release artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `/dev/shm/f24-full271-release-v3.json` | 36,777,928 | `c3b47ff90c15b11111bb49ed88cae098325eae04bcb3d14dd36558ebf2b13d9e` |
| `/dev/shm/f24-full271-release-v3.audit.json` | 1,263,116 | `8b5771265b453b59034de7879a92863197a05aba958e18a8fb0307f44474bee7` |
| `/dev/shm/f24-full271-release-v3.sqlite3` | 52,039,680 | `2a24049f8183bfad72dbb99b77083b462be4106ae781bb82633a2d2164d31433` |
| `/dev/shm/f24-common204-release-v3.json` | 27,342,399 | `52063d74fb7da19fbd3cf7df4d30855356b7b870a049474a7108f6afeac0ca17` |
| `/dev/shm/f24-common204-release-v3.audit.json` | 912,827 | `b46d21e1e43d5688f6472aa41f679be4ef1cbe811d83722e7e176d86b77e6258` |
| `/dev/shm/f24-common204-release-v3.sqlite3` | 38,273,024 | `24ca557b2211d72673e23984426155f0155b8a7479bc98972f19defa40aac681` |

## Family-local release hashes

| Path | SHA-256 |
|---|---|
| `config/families/tm-entrusted-investment-risk-capital-topology-v1.json` | `2e2aa1ecde225686dab312af2bc6b43f125654fdd00bf1e2180e445276c581a5` |
| `config/families/tm-entrusted-investment-risk-capital-evaluation-v1.json` | `068f843ee764b2fda7db85df2c21eb213baf802f1e0c76d1a7d614fa387ac5fc` |
| `config/families/tm-entrusted-investment-risk-capital-schema-binding-v1.json` | `72fdf16a493cb535345e3a6430313f8df6d3912d65369a59c99105137da66e9c` |
| `config/families/tm-entrusted-investment-risk-capital-source-repair-v1.json` | `8afdedb2979d3533328ae2f9fad0540b95d05e6681e00a08e45926beaa4dd865` |
| `config/families/tm-entrusted-investment-risk-capital-pdf-residual-audit-v1.json` | `837e77d433fdf0e7ed51093fef25655ceb138dec9617aa9b0ac4c010caf257e0` |
| `config/families/tm-entrusted-investment-risk-capital-common204-pdf-residual-audit-v1.json` | `c34b6a06d5b8cbba8485b0b2d1933ced29eaed41b1a65eb2967a0199130688ee` |
| `src/bctc_ai/evaluation/gemini_json_entrusted_investment_risk_capital_family_v1.py` | `71f4a0c82977394f77983aaf91d6d775e7cf7389b9c5bd328a9c317a3f1513e9` |
| `scripts/experiments/run_gemini_json_entrusted_investment_risk_capital_accounting_family_v1.py` | `23d773ff2f93dffbe192c43499fcb0a1c068fa09a8d6ed5f373c5f88dec8bf53` |
| `tests/unit/test_gemini_json_entrusted_investment_risk_capital_family_v1.py` | `c51b002baf7d3f0be8c5fdd059d38358548f61867132c8c6372d374a8a1777fa` |
| `tests/unit/test_run_gemini_json_entrusted_investment_risk_capital_accounting_family_v1.py` | `9b7c05099681d4cd7c6cf045205c68ffa979d685bb44361274c4ae52712c05ff` |

## Verification and historical safety

- Family 24, source-observation-contract, and pinned generic-runner suites:
  44 passed in 0.79 seconds.
- Historical artifact/variant/scanner safety: 14 passed; two live exact-release
  pins were run separately from their fixture workspace.
- Both historical live replays retained byte-equal `trials` and `metrics`.
  Whole-result pins failed only because the concurrently updated live schema
  authority moved from `UNIVERSAL_BANK_BCTC_SCHEMA@6074` (1,953 schema / 1,719
  TM items) to `@6076` (1,955 / 1,721), changing 17 authority fields and the
  result ID. This old-corpus pin drift is safety-only and excluded from the
  full271 conclusion.
- Ruff on all Family 24 implementation/runner/test Python: pass.
- Both terminal runners replayed exact sources from the stored family database
  and revalidated the observation contract before exit 0.

## Conclusion

Every initial NOT_OBSERVED or UNRESOLVED document and every PDF-visible Family
24 row was classified. Full271 has zero unresolved documents and zero visible
schema-mappable rows left behind. The 71 residuals are source-SHA/page-render
authenticated documents whose primary statements visibly contain no
schema-mappable Family 24 root.
