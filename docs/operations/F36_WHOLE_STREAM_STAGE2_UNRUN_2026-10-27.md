# F36 whole-run streaming prototype: stage 2, UNRUN

This extends the isolated stage-1 source on branch
`codex/f36-streamed-whole-v1`, parent `95997badb103b2f1fcd545653e812c4ff4a1fad3`.
It is source only. Its author ran no Python, imports, compilation, AST checks,
lint, tests, SQLite, corpus, PDF, WSL, provider or data job and made no commit.
All earlier failures and source/output artifacts remain retained. No memory,
speed, disk-fit, financial acceptance, family seal or integration is claimed.

## New family-local APIs

`evaluation/gemini_json_f36_notes_stream_store_v1.py` adds:

- `ingest_f36_notes_streamed_sweep_v1(path, spool_report=...,
  compiled_specs=..., implementation_refs=..., producer_refs=...,
  run_kind="EXPERIMENTAL")`: exclusively create one schema-compatible derived
  database for the complete original axis, independently rebuild every trial,
  compare exact canonical bytes, insert complete normalized traces, compare
  complete query/count/material/sweep domains, and commit one proposal run.
- `open_f36_notes_streamed_run_v1(...)`: hold/authenticate the committed store,
  repeat the fixed fresh cold reconstruction, check the complete BLOB and every
  normalized row, then expose `reader.original_trial(original_ordinal)` within
  the live context. The accessor expires on exit. Future projection must remain
  inside this context and defer publication until the context exits successfully.
  This stage adds no workbook/projector or publication grant.

There is no supplied source factory, evaluator, callback or caller PASS flag.
The internal factory reloads the original complete corpus selection, PRIMARY
context and live pinned config. It uses the stage-1 per-document iterator with
the unchanged full topology/requested axis and original ordinals. No subset
topology or denominator is manufactured. Each trial's actual financial, ROOT,
inventory, source, classification and retention checks remain the old checks.

`implementation_refs` retains the old sorted identity axis and run-ID grammar;
it must include the exact actual replay adapter ref, as the old checked store
required. An existing valid adapter-only axis remains valid.
The separate `producer_refs` must enumerate exactly every Python source file in
the current `src/bctc_ai` package, with actual byte hashes and sizes. These pins
do not change the legacy run-ID domain. Inputs also include both spool refs,
the index, source database, PRIMARY database, production specs, notes config,
frontier receipts, selected document manifests and the complete selected
selection-history file axes. Held descriptors retain full SHA-256, path and
six-field identity barriers. Source/PRIMARY SQL integrity and foreign keys are
freshly checked before and after cold replay. SQLite sidecars fail closed.
Producer import origins and the code path axis are fixed during each context.
Production callable/class/source-method bindings captured at module import are
also checked; replacing the real iterator, source class or loader with a saved-
trial callback cannot supply cold proof. The new route's private IO seams are
excluded from that binding snapshot, allowing explicit boundary-failure tests.

This is a cooperative exclusive-owner API. It does not isolate arbitrary
hostile in-process mutation. The caller still needs the root runtime lease,
the reviewed clean imported source, and external no-writer ownership. No runtime
or resource-control wrapper is introduced or implicitly authorized by this file.

## SQLite and exact bounded readback

The family-local writer reuses the existing schema string without editing any
generic store, canonical helper, default dispatcher or frozen file. It creates
an exclusive empty destination and initializes only the schema/identity first.
The run, exact-sized whole-sweep `zeroblob`, every original trial, candidate,
mapping and the single EXPERIMENTAL execution are one transaction. Whole-BLOB
bytes use `blobopen` chunks; whole-BLOB `SELECT` and whole-sweep JSON parsing
are absent. Insertion and replay failure roll the transaction back, leaving the
new empty schema for diagnosis. Destinations are never resumed or overwritten.

Before commit, readback checks exact schema, complete run metadata, all counts,
chunked whole-BLOB bytes/hash, every column and byte of every trial/candidate/
mapping, no extra rows, fresh SQL integrity and no selection/export rows. Trace
and scalar byte sizes are checked in SQL before retrieving their variable-size
values. Original trial allocations remain bounded by the declared stage-1
64-MiB trial ceiling. Stored sweep bytes retain exactly two terminal LF bytes;
trial/material/query hashes retain the old one-LF domains. All control inputs
are snapshotted and late caller changes fail closed.

All held-source/spool/control final checks close before transaction commit.
The writer then reopens the committed database and repeats the complete bounded
persisted readback under freshly held inputs. A failure in this post-commit
readback raises and emits no returned receipt; the already committed experimental
database is retained as a failed artifact. It is never selected OFFICIAL. The
separate reader always performs cold replay again and cannot admit such a run
using a prior success flag. This explicit commit boundary does not claim that
post-commit failures can be rolled back after the fact.

No API inserts OFFICIAL execution, family-current-selection, selection events
or exports. A valid proposal is still not financial/canonical acceptance.

## Authored validation and remaining owner work

`tests/unit/test_f36_notes_stream_store_v1.py` defines actual tiny-source old/new
goldens across full/compact and annual/interim-Q4 inputs: exact run/sweep IDs,
whole stored BLOB, every normalized trial/candidate/mapping field and the bounded
accessor. A separate fixture independently ingests two real source documents to
prove complete original-axis behavior, including a persisted explicit outside-
request slot while retaining the same two-document source axis and whole bytes.
No positive financial/source-replay
validator is mocked. A private comparison test reconstructs actual source first
and then injects missing, duplicate, reordered and extra trials; the public route
never accepts this seam as a callback. Public negatives cover newly changed
actual PRIMARY and attempted replacement with saved trials; late spool, frontier,
compiled/query and selection-history mutations; source/PRIMARY sidecars; whole
BLOB, normalized field/bytes/count, schema and execution tamper; exclusive
destination and OFFICIAL/no-callback/complete-producer-pin fences. All are UNRUN.
Late rollback tests assert that the injection occurred within an active
transaction after run/trial rows existed, then require every proposal row gone.

Root must independently review the exact source, then run focused old/new tests
and bounded same-full-axis actual-document equivalence under the authorized
AS 2-GiB development lease. Measure largest-document allocation/RSS/AS, total
package/selection descriptor count, source/hash/SQL time and SSD peaks. Budget
both canonical spools, whole BLOB, duplicated normalized traces, journal and
source authority files. A byte ceiling is not proof that the document allocation
fits. No cap increase or whole-run retry is authorized here. The approximately
400-MB canonical whole sweep remains one run; the earlier 21 batch sweeps do
not establish whole-run acceptance. Source/PDF/residual/legacy/financial and
full/common terminal gates remain unfinished.
