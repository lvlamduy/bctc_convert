# Experiment log

| ID | Date | Hypothesis / test | Evidence and result | Decision |
|---|---|---|---|---|
| E-0001 | 2026-08-05 | Preinstalled PyTorch can execute on RTX 5070 Ti | PyTorch 2.5.1+cu124 lists through `sm_90`; a real CUDA tensor operation failed with no kernel image for `sm_120` | Reject this runtime; isolate a newer CUDA build |
| E-0002 | 2026-08-05 | Quality-gated preprocessing can preserve a clean scanned/mixed page | A real ACB page rendered, hashed, assessed CLEAN, and passed checkpoint verification; original retained | Keep conditional preprocessing; do not transform every page |
| E-0003 | 2026-08-05 | Born-digital word geometry is usable for borderless statement reconstruction | A VPB report exposed high-quality Vietnamese words and stable right-edge value columns; generic `find_tables()` merged borderless content incorrectly | Implement word-geometry row/axis reconstruction; keep table finder as a proposal only |
| E-0004 | 2026-08-05 | Uploaded Mongo archive can provide weak structural/reference evidence | Archive SHA-256 registered; official tools dry-run found 25 namespaces; allowlisted template restore produced 1,851 documents; ID 1944 collision count is zero | Use only allowlisted financial collections and never overwrite PDF evidence |
| E-0005 | 2026-08-05 | `vst_level` can supply validated parent/order support | Four workbooks contain 1,535 covered IDs/edges; no duplicate ID, missing parent, or non-self cycle; LCTT is explicitly direct-branch-only | Import as supporting hierarchy with source hash and partial-coverage flag |

New rows must link to detailed machine-readable artifacts when metrics become non-trivial.
