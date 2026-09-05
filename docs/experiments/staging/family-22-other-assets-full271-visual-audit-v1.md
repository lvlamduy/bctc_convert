# Family 22 — other assets full271 visual audit v1

This ledger seals Family 22 (`OTHER_ASSETS`) on the immutable 2025–2026
corpus. No provider was called. Source PDFs and selected Gemini JSON were read
only. Results are experimental schema-mapping proposals, not canonical or
export authority.

## Authenticated inputs and ownership boundary

- Full271 index:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`
  (422,971 bytes; SHA-256
  `969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`).
- Common204 index:
  `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json`
  (317,566 bytes; SHA-256
  `acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1`).
- Both terminal runs used frozen shared multitable evaluator SHA-256
  `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`
  and generic runner SHA-256
  `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.
- The historical E-0073 and E-0127 eight-bank artifacts are authenticated as
  a disjoint safety oracle only. Their 16 source SHA-256 values have zero
  overlap with full271 and common204. They are excluded from the current-corpus
  conclusion under comparator policy `DISJOINT_EXPANSION`.

Family 26 (`LOAN_INTEREST_ACCRUAL_CLASSIFICATION`) exclusively owns RNIDs
982–986 and the five interest/fee receivable roles. Family 22 removes every
binding for those RNIDs. `INTEREST_FEE_RECEIVABLES` remains only as an
unbound, validation-only structural bridge because it is a declared component
of the visible RNID 966 Family-22 root. It cannot emit a mapping.

## Baseline and remediation

The post-split baseline
`/dev/shm/f22-full271-split-baseline.vH8ACE/sweep.json` was 195 READY / 69
NOT_OBSERVED / 7 UNRESOLVED / 1,293 mappings (53,399,707 bytes; SHA-256
`811c2cbc754f65e2860ccf747697c38957f25bb73e421721598dd4c8df99338b`).
The terminal result converts all 76 residual documents to READY and adds 254
source-bound mappings. The 195 already-READY documents remain READY.

The declarative topology/config expansion is generic: aliases are scoped by
declared parent role, hierarchy path, owner/reset fence, lane axis, and unit.
It does not route on bank, filename, year, document ordinal, note number, or
numeric value. The Family-22 adapter covers two exact source structures:

1. A page-leading table marked `CONTINUES_FROM_PREVIOUS_PAGE` may join only the
   immediately preceding selected and physical page's final MONEY table. The
   receiver must be the first MONEY table, have a terminal total, carry
   declared Family-22 roles, and have either the exact same explicit
   period/unit axis or a completely blank header axis that inherits an exact
   prior axis. The source cells and coordinates do not change. Full271 has 15
   such receipts: 14 exact explicit axes with an omitted sender marker and one
   blank receiver axis with an exact two-sided marker.
2. An explicitly headed provision table is authenticated as a different
   source population. Full271 has 57 two-period provision-only controls and
   six four-column period × asset-balance/provision risk-subset controls. The
   latter six bind all four original columns and every role-hit row but emit no
   Family-22 mapping: the displayed gross risk subset is not the full carrying
   balance. Unknown headers, reordered/duplicate metrics, an ambiguous role,
   or a Family-root row fail closed.

Adapter normalization runs on canonical clones, reseals component regions and
outer query evidence, and is required to replay byte-identically before
storage. Negative fixtures cover nonadjacent pages, conflicting axes,
nonterminal receivers, ordinary non-provision headings, malformed metric
axes, receipt tampering, and input mutation.

## PGB carrying-balance correction

An early checkpoint incorrectly treated two PGB note 15.2 provision movements
as RNID 987 carrying balances. It was stopped before acceptance and is retained
only under `/dev/shm/f22-invalid-b898-v1/` as explicitly invalid evidence.

The generic exact provision heading now includes `Dự phòng rủi ro cho các tài
sản Có khác`. The accepted result maps the visible `Tài sản Có khác` row in the
preceding carrying-balance table and classifies note 15.2 as source-only:

| Full ordinal | Accepted RNID 987 source | Accepted values | Excluded provision total |
|---:|---|---:|---:|
| 142 | physical p36, `s2:t1:r5` | 111,897 / 129,801 | p37, 206,521 / 58,481 |
| 143 | physical p35, `s2:t1:r5` | 107,189 / 129,801 | p36, 149,736 / 38,481 |

The semantic correction receipt is
`/dev/shm/f22-pgb142-143-semantic-correction-receipt-v1.json` (14,235 bytes;
SHA-256 `3cb84b4b61b8018b47b08bb1b59e11944afb409d90a30599292c30017e6e6ad0`,
ID `f22pgbcdv1:receipt:166793a396c1a54a04fccb74a7fea579f816b0f49304170df34143a686745c78`).
It proves that these two RNID 987 sources are the only mapping-semantic changes
between the invalid checkpoint and accepted v3; the other 269 trials are
unchanged.

## Visual and no-left-behind gates

The original full adapter visual manifest covers 73 source PDFs, 88 rendered
pages, all 15 continuation receipts, and the prior 61 provision receipts:

- manifest `/dev/shm/f22-full271-adapter-visual-v1/manifest.json`, SHA-256
  `7ec9394c341203b1a5c1513e32221bbee5711b4b19f674b47f3fc4999eaf66cf`,
  audit ID
  `f22favav1:audit:349c615dc95c963115bbcaea98876e7d9df3e299ac85a9a17c1a2ab0b86f6266`;
- visual review
  `/dev/shm/f22-full271-adapter-visual-v1/visual-review-receipt-v1.json`,
  SHA-256
  `ca5eaa3fa8f27c368a264905db5ead86f678dd28ec837ef5f3488a61b5773600`,
  review ID
  `f22favrev1:review:51dd70b97766ad68ec5a6601ecd7088b3660f5c27065980ac134ea494a36d0b5`.

All those receipt IDs are an exact subset of accepted v3. The two new PGB
documents were rendered from source-SHA-authenticated PDFs at 200 DPI in RGB
with no alpha. Their four carrying-balance/provision images were inspected at
original resolution. The content-addressed rebase receipt
`/dev/shm/f22-full271-adapter-visual-v3-rebase-receipt.json` (20,253 bytes;
SHA-256 `424ae5cb3d65a04deadc1455790fd8bcb411e525e22ee3e11f8fe973e83e8c2d`,
ID `f22favrbv1:receipt:0bebf3d8555e44ee164552bece8823f0882d0b3076147d418570d65406283ba6`)
therefore covers 75 adapter documents / 92 renders / 15 continuation receipts /
63 provision controls with zero visual contradictions and zero unreviewed
adapter documents.

The narrower pre-release residual audit remains useful corroboration:
`/dev/shm/f22-adapter25-closure-audit-v1.json` (SHA-256
`c173c8fb0c4562ff1a0c76ba2f0d6cc4e48f16354f3fc8ad7042c7cdcc4ee104`,
ID `f22a25cv1:audit:5d0aa26d043878cdbd8d29efa8a6c45228def4f434cb9b41a0036303efe58c39`)
converts 25/25 U to READY with 196 mappings. Its 40 rendered pages prove the
15 continuation and 12 provision dispositions; VBB ordinal 257's receiver
interest-detail rows produce zero Family-22 or RNID 982–986 source refs.

The specialized runner adds an exhaustive selected-source role-hit contract.
Every configured role hit in every declared MONEY-table inventory row must be
one of: direct mapping, exact-equation evidence, hierarchical duplicate proof,
validation-only bridge, source-only receipt, typed all-blank omission, exact
adapter control, or an explicit query owner/control exclusion. A visible
unconsumed subtotal is a hard error. An unreferenced structural group is
permitted only when every source lane is truly blank, and its receipt retains
the original null cells.

| Corpus | Role-hit rows | Adapter tables | Violations | Receipt ID |
|---|---:|---:|---:|---|
| full271 | 5,501 | 78 | 0 | `f22srcrv1:receipt:20e472cf43c67811ca08ba61166d7bb45a428fde35dd936fbcb9a847ba674e22` |
| common204 | 4,271 | 66 | 0 | `f22srcrv1:receipt:aeb575c8e7b12fad54c0db9d165048275e594e0b4ae551876760afacda34c2b7` |

Full271 dispositions are 1,302 direct schema sources, 154 validation-only
bridges, eight exact-equation rows, two hierarchical duplicate proofs, 40
source-only receipts, 13 provision-control role hits, 29 typed optional blank
omissions, 22 all-blank structural non-observations, 3,137 owner-fence
exclusions, and 794 typed-control exclusions. No visible schema-mappable row
is left untyped or unconsumed.

## Terminal release and durable stores

Both authoritative runs completed on 2026-09-04 UTC under
`DISJOINT_EXPANSION`:

| Corpus | Documents | READY | NOT_OBSERVED | UNRESOLVED | Mappings | Equations | Continuations | Provision controls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full271 | 271 | 271 | 0 | 0 | 1,547 | 814 | 15 | 63 |
| common204 | 204 | 204 | 0 | 0 | 1,216 | 643 | 12 | 54 |
| full-only expansion | 67 | 67 | 0 | 0 | 331 | 171 | 3 | 9 |

Full271 IDs are sweep
`gjfafsv1:sweep:e48b1d433e348ed192fb7acf853006e8b62bc6578c8ce5e89268da856ce797c7`,
audit
`goaav1:audit:76a388e1ec7a3e0f58a27b22c6387feafefd2a32020d5fdf510aa9909551d353`,
and run
`gjfafstorev1:run:2bab75410999b7fe3e772cc160a0d858eea0f5b8946ec35df5c4d901e4b56b24`.
Common204 IDs are sweep
`gjfafsv1:sweep:6bec476edfec94e887506b5e131820c8ceba00fd79ab58c24b92ef31aa1a012f`,
audit
`goaav1:audit:38ab3370b92ef2b2a0df8273bd2e0f2970da0419762058a30930f9b63b57ca0f`,
and run
`gjfafstorev1:run:db8991ef07d5156e65c4649037041eec6c8884fd159ce2a6907e3ded4f719df7`.

| Artifact | Size (bytes) | SHA-256 |
|---|---:|---|
| `/dev/shm/f22-bb319-full271-v3.json` | 60,981,461 | `57cb2d35de68cf366427adfec1358a230304a374191b9bf49d3359c47ea24a41` |
| `/dev/shm/f22-bb319-full271-v3.audit.json` | 17,386,659 | `bc2f87efe23a8a959fef9ee5f36e7b12b383a90a85166995c291dc74c640ef6f` |
| `/dev/shm/f22-bb319-full271-v3.sqlite3` | 112,824,320 | `9d0f38ab456688d1393b5958aca6ac247ddf6042ea3eb08f22af7ddb15faed5d` |
| `/dev/shm/f22-bb319-common204-v3.json` | 46,996,713 | `bc7c0576b2429654a34cf5656c7609a261e672894dd4a0cd5df2aa39c015dfb8` |
| `/dev/shm/f22-bb319-common204-v3.audit.json` | 13,642,876 | `5c0605c4c1619f87214556b120e0e91292abe933a52946bb710d7e72be03d9aa` |
| `/dev/shm/f22-bb319-common204-v3.sqlite3` | 87,445,504 | `0147f35b1747462f62554ac9bb4f9b3b62a7262569eb925d53cef4dd25c1d5bb` |

Both stores returned `PRAGMA quick_check=ok` and an empty foreign-key check.
The runner rebuilt trials from the immutable source-page database, required
typed equality with evaluated trials, loaded each stored sweep back, and
required exact typed equality before registering the export.

## Semantic expansion and source-observation contract

The content-addressed common/full receipt is
`/dev/shm/f22-bb319-common204-full271-semantic-expansion-receipt-v1.json`
(16,051 bytes; SHA-256
`e4f949d01e21b00ded5fee9358713c5c105cd9afe3c1f1de92e985b04203368e`,
ID `f22cfsrv1:receipt:3e827e580655fe4019397b3fd677f953944bb19cba42101a3ff01f4af27b8ada`).
All 204 common source SHA trials have byte-equal status/reason/RNID/role/unit/
value/source-surface projections in full271. Twenty-four selected page-JSON
frontiers differ. Only KLB common ordinal 41/full ordinal 64 changes an
extractor page-version ID and source row kind; its physical page/table/row,
label, hierarchy path, values, units, RNIDs, and roles remain exact. This drift
is explicitly recorded and is not projected into silence. Full271 has exactly
67 additional sources and 331 additional mappings.

The global source-observation contract passed with zero violations:

| Corpus | Mapping occurrences | Cells | Partial mappings | Source blanks | Derived cells | Violations |
|---|---:|---:|---:|---:|---:|---:|
| full271 | 3,094 | 6,188 | 62 | 62 | 80 | 0 |
| common204 | 2,432 | 4,864 | 46 | 46 | 72 | 0 |

Every partial mapping retains a typed null `BLANK_SOURCE_CELL`; all-lane blank
roles are omitted. Printed dashes remain source-observed zero. No equation,
sub-total, or root control turns a blank cell into numeric zero.

## Family-22 / Family-26 cross-family gate

The same-corpus cross gate rejects any Family-22 RNID 982–986 mapping and then
hashes exact `(source, page, section, table, row, RNID)` axes for both families.

- Full271: Family 22 axis 1,680; Family 26 axis 631; overlap zero. Receipt
  `/dev/shm/f26-bb319-full271-v1/f22-cross-family-disjointness-receipt-v3.json`,
  SHA-256
  `4bf24d62f5908a352253c48058ebe2f887d9f3be8608bf4217796823bf52474f`,
  ID `glicacfdv1:receipt:1451cfece5f0b9cfda587ff8c7b9bb0fb991839bdf990656582b4e7c0930f39d`.
- Common204: Family 22 axis 1,320; Family 26 axis 454; overlap zero. Receipt
  `/dev/shm/f26-bb319-common204-v1/f22-cross-family-disjointness-receipt-v3.json`,
  SHA-256
  `41516487757220bbacaf63110a6ceaebe911369c311d9e045003e2fabf9bc7f4`,
  ID `glicacfdv1:receipt:a2031c7dd9e16bf229b402d3d0c64a2d973c108689b59085e344087ed83bf952`.

Family 26 independently finished full271 at 271 READY / 0 NOT_OBSERVED / 0
UNRESOLVED / 561 mappings (run
`gjfafstorev1:run:7184e113991328848123d11587f0b18a0b0a9b033222cfc563b9bb02f52c6b9e`)
and common204 at 204 READY / 0 NOT_OBSERVED / 0 UNRESOLVED / 402 mappings
(run
`gjfafstorev1:run:89b98246b36e583b606f274cb85af2c27a5b6148295204ddd6659b1574354b59`).
Both source-observation contracts have zero violations; both stores have clean
integrity and foreign-key checks. The exact split therefore preserves
Family-22 root closure without double-mapping any Family-26 row.

## Family-local release hashes and verification

| Path | SHA-256 |
|---|---|
| `config/families/tm-other-assets-topology-v1.json` | `ca18ee03766a1f3a08efe8e1f972a02245dee78fa89b5e2d57dadbd0785270cd` |
| `config/families/tm-other-assets-evaluation-v1.json` | `be642156424f10e9690cbff921f6bbb12cc9767e23833a62153d41b4470b28ac` |
| `config/families/tm-other-assets-schema-binding-v1.json` | `21e18a6c0ff1e38b3596fd1b07e9ee3a388830c2191aeec008e979793e173b2f` |
| `config/families/tm-other-assets-pdf-residual-audit-full271-v1.json` | `3e7cbe6e74a3080043fccdf41c1c98d510a55e129c355241538533ce7ee37f5d` |
| `config/families/tm-other-assets-pdf-residual-audit-common204-v1.json` | `f330ac74f0a211e68e882ec915806e21b663d0fbd2a47effd054448c21533a7c` |
| `src/bctc_ai/evaluation/gemini_json_other_assets_family_v1.py` | `8efe2c890d124b9c0b24971c98db1e341eeccb272d752b653c712d68d9042c7a` |
| `scripts/experiments/run_gemini_json_other_assets_accounting_family_v1.py` | `9281b6a0d711843e5ff209ea2fa13e0be969e3bcce401943a9216fbe6d7be8eb` |
| `tests/unit/test_gemini_json_other_assets_family_v1.py` | `eb7d6f75b2fbe9ec0dbb1b4a6107b5f4e50cc152ff5b858c0c551a1868b1ca49` |
| `tests/unit/test_run_gemini_json_other_assets_accounting_family_v1.py` | `c1f729b550fb5b4f2996ca2ad477c6062259e74b5ea104893f8073dd62d7ef21` |

- Family evaluator, specialized runner, and global source-observation contract:
  43 passed in 0.65 seconds.
- Python byte compilation: pass.
- Ruff on all Family-22 implementation/runner/test files: pass.
- Family-owned diff check: pass.
- Both PDF residual specs contain zero entries because every full271 and
  common204 document is READY; the exhaustive role-hit and visual gates above
  remain mandatory rather than treating an empty residual set as sufficient.

## Conclusion

Family 22 is terminal on both corpora. Every baseline false-N/U became READY,
every selected source role hit has a typed disposition, all partial blank lanes
remain null, and every adapter-touched source population is visually bound.
The exact Family-26 split has zero mapping overlap. No visible,
schema-mappable Family-22 row is left behind.
