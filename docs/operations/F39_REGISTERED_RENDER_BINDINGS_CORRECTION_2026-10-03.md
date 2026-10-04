# F39 additive source-repair render metadata correction

This is a family-local replay metadata correction after restore preflight PASS,
not an amendment to the migration manifest or the base Git history. The base
commit remains `8efd618b6c77f0cdbb402a440e7ba3b3549184f1`.

The original registered source-repair file remains byte-for-byte unchanged at
SHA-256 `9aac4e448b82ee0078c007ca06a36f0e3f11c2b4f694266a1211929f16228ea4`.
Its global PyMuPDF RGB/alpha-false PNG matrix declaration is `[2, 2]`. A fresh
finite comparison against the existing renderer's matrix `300 / 72` reproduced
every registered full-page PNG, dimensions and crop RGB hash exactly and uniquely:
two repairs use the declared matrix; eleven use the existing 300-DPI matrix.
The diagnostic did not search arbitrary render settings or change any hash.

The diagnostic receipt is
`/srv/bctc-receipts/f39-render-profile-probe-22b81e8b83e845ab97519587f9ee831b/F39_REGISTERED_RENDER_PROFILE_DIAGNOSTIC.json`,
SHA-256 `9bdeb27d28ca2b7fd3eafe296a9091afe6ff94a2e2d62b145165e380c475aad9`.
It authenticates all five original PDFs before and after rendering and all
thirteen existing repair IDs. No PDF or JSON was regenerated or changed.

An additive correction was written outside the repository first:
`D:/bctc_bank/restore-receipts/F39_SOURCE_REPAIR_RENDER_BINDINGS_CORRECTION_2026-10-03.json`.
Its exact repository copy is
`config/families/tm-income-tax-source-repair-render-bindings-v1.json`, SHA-256
`a714e256ad3b508fba5b331e27551433824b8db14d84ea9cade28a296b7cf249`.
The companion `.json.sha256` authenticates the external receipt bytes without
an impossible self-referential file hash.

The F39 runner pins this additive file, binds the entire ordered original repair
frontier and original source-repair specification, then uses each declared
profile exactly once. Full-page image and crop hashes, source-PDF identity,
selected page JSON, locator and before-exact source row must still match the
original registered evidence. There is no automatic profile fallback and no
replacement of an expected image hash to accept newly rendered pixels.

Scope is exclusively render metadata for these pre-existing F39 repairs.
Source values, before/after repairs, repair IDs, image/crop hashes, raw Gemini
JSON, other family pins, shared files, S3 migration objects and base history
are unchanged. The correction does not authorize providers, inference from
equations, blank-to-zero conversion or family-terminal acceptance.
