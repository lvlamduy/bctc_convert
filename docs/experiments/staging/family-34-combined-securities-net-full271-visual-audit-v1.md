# Family 34 — combined securities net full271 visual audit v1

This ledger seals Family 34 (`COMBINED_SECURITIES_NET`, root RNID 5990) on
the immutable 2025–2026 selected-JSON corpora. No provider was called. Source
PDFs, selected page JSON, and page stores were read only. Results remain
experimental schema-mapping proposals, not canonical or export authority.

The governing semantic rule is intentionally strict: Family 34 may be mapped
only from a direct, source-visible combined trading-and-investment-securities
net presentation. A missing RNID 5990 is never created by adding Family 32 and
Family 33 results, by treating nearby lines as one row, or by narrowing a
broader segment/geography result.

## Authenticated inputs and baseline

- Full271 index:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`
  (422,971 bytes; SHA-256
  `969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`).
  It binds 271 documents / 14,945 selected pages and a 573,145,088-byte page
  store with SHA-256
  `ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`.
- Common204 index:
  `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json`
  (317,566 bytes; SHA-256
  `acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1`).
  It binds 204 documents / 11,454 selected pages and a 553,984,000-byte page
  store with SHA-256
  `a14904a492e6beae165b81f7aa1738352a9824e113f1b163a46ee277d37e0220`.
- The direct full271 baseline was 0 READY / 271 NOT_OBSERVED / 0 UNRESOLVED,
  with zero candidates and zero mappings. The final result is unchanged
  because the source audit found no direct Family-34 presentation to recover.
- The legacy 140-trial audit figure supplied for comparison was 12 READY /
  128 NOT_OBSERVED / 0 UNRESOLVED. It is not treated as a current-corpus
  numerator. The fixed historical artifacts are authenticated only under the
  disjoint-corpus policy described below.

The shared multitable evaluator and generic runner were used read only at
SHA-256
`bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`
and
`d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`
respectively.

## Direct-presentation and false-positive audit

The Family-34 topology already requires an explicit combined parent and the
two declared trading/investment net roles inside that parent cluster. The
family-local change adds two exact hard negatives observed in the current
frontier:

- `Chứng khoán kinh doanh và chứng khoán đầu tư - gộp` is an asset/geography
  row, not an income-statement net result; and
- `Lãi thuần từ hoạt động kinh doanh ngoại hối và mua bán chứng khoán kinh
  doanh và chứng khoán đầu tư` includes foreign-exchange activity and cannot
  be narrowed to RNID 5990.

The selected primary-income-statement census is exhaustive:

| Corpus | Separate trading + investment rows | Investment row only | Neither | Direct combined row |
|---|---:|---:|---:|---:|
| full271 | 223 | 36 | 12 | 0 |
| common204 | 169 | 25 | 10 | 0 |

The full census classified 504 source rows across 53 exact spellings: 234
trading rows and 270 investment rows. None is a direct combined result. Its
content-addressed working receipt is
`/dev/shm/f34-primary-presentation-census-v1.json` (205,618 bytes; SHA-256
`29808874c89e0ab7af31775e764754cf148821fb14ba13960a6c8f629c9b64a9`).
The common204 receipt is
`/dev/shm/f34-primary-presentation-census-common204-v1.json` (162,154 bytes;
SHA-256
`ff2acbe9fecd635db93d8fbe2c89e348dacaaea059c6efb85c34a06209754c7f`).

An independent scan over all 14,945 selected pages found 38 rows in 30
documents whose literal label contains both `chứng khoán kinh doanh` and
`chứng khoán đầu tư`. All 38 occur in `FINANCIAL_NOTE` /
`NOT_APPLICABLE`, never in a primary income statement. They comprise NAB/STB
geographic asset concentrations, SSB segment asset rows, and four TPB segment
profit rows that also include foreign exchange. Thus none is a narrower
Family-34 source result. The two dangerous label shapes are covered by exact
negative tests; no bank, filename, note number, page, or value is used as an
acceptance rule.

## Complete PDF and visual residual gate

Every final N/U source PDF was inspected; there are no U documents. The
registered full271 residual spec binds all 271 source PDFs by logical path,
SHA/size, trial status, and complete full-document text-scan result. It also
binds every selected primary-income-statement page by selected page-JSON ID,
physical page, and PyMuPDF RGB 1x PNG render SHA:

- 15,578 total PDF pages were scanned; 154 pages exposed extractable text and
  121 PDFs were fully image-only;
- 306 primary-income pages were rendered and visually reviewed, covering 236
  documents with one review page and 35 with two; and
- 58 bank-grouped contact sheets cover all 306 page renders. Every sheet was
  inspected at original detail. Visible presentations show separate Family-32
  and Family-33 lines, or an investment line without a trading line; none
  shows a direct combined Family-34 result row.

The full271 bank denominator is ABB 12, BAB 10, BVB 14, EIB 16, KLB 16,
LPB 7, MSB 16, NAB 16, NVB 16, OCB 16, PGB 7, SGB 14, SHB 16, SSB 16,
STB 16, TCB 16, TPB 16, VAB 15, and VBB 16.

The common204 residual spec independently binds 204 PDFs / 11,987 total PDF
pages / 230 primary-income renders. Eighty-six PDFs are fully image-only; 178
documents have one review page and 26 have two. Both registered specs have
exactly one disposition for every residual:
`NO_DIRECT_COMBINED_SECURITIES_NET_RESULT_ROW_IN_BOUND_REPORT`.

The full-document text receipt is
`/dev/shm/f34-pdf-text-scan-v1.json` (81,484 bytes; SHA-256
`0e18ccb676c7b29c48dfe0d2fba516a942bc4168c547f0292e221681511a994f`).
It authenticates 271 PDF SHA/size pairs and has zero direct target-phrase
hits. Text absence is only a challenger; the pixel review is authoritative
for image-only and nearby-line cases.

The authoritative runs used the project environment with PyMuPDF 1.28.0 /
MuPDF 1.29.0. An earlier non-authoritative system-PyMuPDF attempt failed
closed on render drift and was discarded; no result from it was accepted.

## Terminal results and source-only inventory

Both authoritative runs completed on 2026-09-04 UTC:

| Corpus | Documents | READY | NOT_OBSERVED | UNRESOLVED | Mappings | Candidates | Equations | Source-only rows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full271 | 271 | 0 | 271 | 0 | 0 | 0 | 0 | 0 |
| common204 | 204 | 0 | 204 | 0 | 0 | 0 | 0 | 0 |

All trials have status
`NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY`, empty reasons, and no
selected candidate. There is no unmapped source-only Family-34 row, no blank
arithmetic, no derived cell, and no residual requiring a source repair. The
zero READY count is therefore a source-presentation conclusion, not a query
policy omission.

### IDs and durable artifacts

Full271 IDs:

- sweep `gjfafsv1:sweep:9cdedffcbb452d9b4f533e587f8a2827699eb6362bb1f53ddcaafc29652a4025`;
- audit `gjcsnauditv1:audit:62b0bbc092b88dc03710653f5fd6059970576ab5e22b1faea0f7ddee8055abd1`;
- store run `gjfafstorev1:run:c15dfb7d64b34dfb1e8b913731f926d8bc029fbd48cdf7cc79106cac4b1a4095`.

Common204 IDs:

- sweep `gjfafsv1:sweep:51ff041b6afbe9790f0aecffda890dd78430affdd75f895fa22cd520f336c0cd`;
- audit `gjcsnauditv1:audit:291d5f236c18675b7a24904f47d0169e5f309fe6d8599c615d50368e7e6d3ac0`;
- store run `gjfafstorev1:run:bf67161c74cc67faacac12642de31bc6ea098ad31f3fa8a185007ba2a55d0e4b`.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `/dev/shm/f34-full271-bb319-v2/family34.json` | 20,181,506 | `3b155a74b67530a6f6ce0c5c8b370efdade0879b0b1071b84ef1bd0b0769f879` |
| `/dev/shm/f34-full271-bb319-v2/family34.audit.json` | 5,064 | `717ee9e602df3a35ff0e7f2f8793e106433c3d3fde9d435e2d9c07a5c685101f` |
| `/dev/shm/f34-full271-bb319-v2/results.sqlite3` | 20,647,936 | `57ec24caa1e3e55e8a256b6c129d69849bae06af1000fa6d7aa90e443b0a04c1` |
| `/dev/shm/f34-common204-bb319-v1/family34.json` | 15,423,017 | `859592d48884c2d2348d49e9daac5ad0df398c0a81c828eda3e476453feda9a3` |
| `/dev/shm/f34-common204-bb319-v1/family34.audit.json` | 5,068 | `1b73ef0c0bfd92c8937af824845244fa32fac368e6af53042671092082d9a9d1` |
| `/dev/shm/f34-common204-bb319-v1/results.sqlite3` | 15,802,368 | `c4094ce02444a3fb428b0ffd06aa067aade6bb31a6aa4095f819fc0216da3ce9` |

Both databases return `PRAGMA integrity_check=ok`, an empty foreign-key
check, and the exact 271/204 trial counts. Each runner rebuilt its trials from
the authenticated source SQLite database through the registered source-replay
callback, required typed/canonical equality, re-authenticated implementation
and source bytes, loaded the stored sweep back, and required exact typed
equality before registering the export.

## Historical, observation, and cross-corpus gates

Historical artifacts E-0086 and E-0141 are authenticated as 16 fixed sources:

- E-0086 (15,453 bytes; SHA-256
  `491965eff2494421c6f95334ed97ccc52333e11c7178f9410cee8cc41c4ca2cf`)
  contains one direct historical MBB presentation and seven bound absences;
- E-0141 (10,803 bytes; SHA-256
  `fc591e1acd8a167b8d252da7eaf30073ae14b1e77630cd6210dec3407b5b6b89`)
  contains eight annual bound absences.

Their source axis has zero overlap with full271 or common204. The enforced
policy is `DISJOINT_EXPANSION`; historical results cannot promote a current
document or alter a current status.

The global source-observation contract passes on both runs with zero mapping
occurrences, cells, blanks, derived cells, or violations. This is the expected
result for a direct-only family with no observed direct presentation.

Common204 is an exact 204-source subset of full271. The canonical projection
of source SHA, status, reasons, mappings, selected candidate ID, and candidate
count has zero missing sources and zero mismatches. The full271 common subset
and independently replayed common204 projection are byte-identical (44,474
bytes), both with SHA-256
`129fd46758006048527c748fd8b61a786baccb6e09fa001eb7f18ac8a76edc96`.
The complete full271 projection is 59,080 bytes with SHA-256
`b65f8956fff209ceeb272d4e83002d6f40a7d376ff246f664371b3d3598beaf3`.

## Family-local release hashes

| Path | SHA-256 |
|---|---|
| `config/families/tm-combined-securities-net-topology-v1.json` | `1548f20949f93fc95f7abed8b10bcd1256331a8e4560420ef51242db855a27a6` |
| `config/families/tm-combined-securities-net-evaluation-v1.json` | `fdc56171979e32a58f0cf412f2cca709a66d89624733b21c375a1a956442a1b2` |
| `config/families/tm-combined-securities-net-schema-binding-v1.json` | `132635ebcfc1819cde965e0098b92231cb93ebddb8aa01ddc5a871dc41dc3072` |
| `config/families/tm-combined-securities-net-pdf-residual-audit-full271-v1.json` | `0cbca4285042e26868887497b564d75ab0c768c539ad300e90890507173dc3e4` |
| `config/families/tm-combined-securities-net-pdf-residual-audit-common204-v1.json` | `9e7d066b40e7647cfb28fdf9461173e89246d67d42d030c19699f287a70d04f1` |
| `scripts/experiments/run_gemini_json_combined_securities_net_accounting_family_v1.py` | `e3933c73bec23601a364b937dc017f46e6eb02e2fc0f9c096ca0c1ed51c123af` |
| `tests/unit/test_gemini_json_combined_securities_net_family_v1.py` | `3f4ef91f8674c90bc3096f555da4169893fd0752e1d02a5ab68b6ce7f5a17f28` |
| `tests/unit/test_run_gemini_json_combined_securities_net_accounting_family_v1.py` | `6b68a1d1c3fcdffa14e274ae4e02f194bdfbfb28f42303d02ab5682376678d33` |

## Verification and conclusion

- Family-34 evaluator/runner plus global observation contract: 34 passed in
  0.46 seconds.
- Family-34, generic multitable/flat/store/runner, structure-scan, variant
  graph, and observation suites: 247 passed in 4.53 seconds. The two legacy
  live-builder tests whose external generated inputs are absent were not used;
  the specialized runner authenticates the fixed E-0086/E-0141 JSON oracles
  directly.
- Ruff, Python compilation, JSON parsing, and family-local diff checks: pass.
- Full271 and common204 PDF authentication, source replay, audit validation,
  store reload, database integrity, and export registration: pass.

Every final N document and every selected primary-income page was checked
against the source PDF. None contains a direct source-visible Family-34 value;
all plausible current-corpus false positives are broader, non-income, or
separate Family-32/Family-33 presentations. There is no visible mappable value
left behind, no blank-to-zero inference, no component backsolve, and no
unexplained residual.
