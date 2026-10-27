# L3b V5 source capture: static review complete, execution pending

Task branch: `codex/l3b-census-v5`, based on the already pushed tools checkpoint
`6aae2295bc5dab886c3e7e78233c02d7d4544c80`. Project production source, family
configurations, frozen files, schema and templates are unchanged by this capture.

Root copied the thirteen frozen V5 packet files byte-for-byte from
`D:/bctc_bank/restore-receipts/CODEX_L3B_CENSUS_20261026_V1/v5`, checking every
source and destination SHA-256 and byte size. Absolute paths in the authoring
receipt describe that historical external authoring location. They are not an
instruction to import external source during tests. Future tests must run this
captured source from a fresh, clean Linux Git clone.

The independent reviewer acknowledged the final frozen packet with no material
finding in the bounded historical-reference delta. This is a static review,
not a test result, source census result or financial acceptance.

Key captured pins:

- Helper: `fcf01afa97feb50eb4d9d3d7109fa1c9aff9906bff54fb51f9c98e3319a6a562` / 46143 bytes.
- Tests: `428047090c8f38e373e939c6f66495a6c444294e3c6c92288bfdab11a010fb16` / 34722 bytes.
- Catalog: `13fc0706cfe231af1eb65335d0a81b77600be68a76be657d730eaa4621259b30` / 551625 bytes.
- Packet checksums: `3510ae75038ccccc20bc300e19803e21fbbd71f3bcca0d9c60c49b26558df06b` / 1236 bytes.

V5 corrects the reader's compatibility with the producer's exact four-field
references: path, SHA-256, byte size and six-integer historical stat identity.
Historical inode identity is preserved as metadata; independent immutable byte
pins and fresh held-file checks remain the authority for current restored files.
The complete inner-receipt equality, full frontier, literal matching rules,
punctuation handling, catalog and corrected UTF-8 synthetic fixtures are retained.

All **40 V5 test methods are UNRUN**. Prior V4's 34 passing methods do not certify
this revision. Prior failed actual attempts remain available, including the
completion-reference failure preserved under the external receipt prefix. They
failed before opening the original inventory stream and produced no census.

Execution requires Claude's explicit `SLOT OPEN`, no competing data job, the
existing serial lease, Python 3.12, address space at most 2 GiB, nice 19, the
memory guard and watchdog. A fresh complete passing synthetic-test receipt is
required before any separately authorized read-only census. No automatic retry,
resource-cap increase, SQLite/PDF access or provider call is authorized here.

The future census inventories existing source-JSON labels for F41-F53. A label
hit grants no financial ownership, numeric mapping, absence proof or family
acceptance. Standalone 2024 reports remain excluded. F41 production stays closed
until the required F39/F36/F37 closure gates pass.
