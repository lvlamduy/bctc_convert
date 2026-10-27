# F36 whole-run streaming prototype: stage 1, UNRUN

Own branch `codex/f36-streamed-whole-v1`, base
`511aa8950886cc455b821f69fa8ad08b15ec2af7`. This is a source candidate only.
No tests, imports, compilation, lint, corpus, SQLite, PDF, provider or WSL job
was executed by its author. There is no measured whole-corpus fit or speed claim,
no family seal and no new financial acceptance. Earlier failed whole-run outputs
and every batch artifact remain unchanged.

The chosen goal is one complete logical F36 run over the original FULL271 or
COMMON204 axis, retaining the same trials, source ledgers, canonical JSON bytes,
query/sweep/run IDs and normalized traces. Batch evidence does not prove that
whole-run contract. Ledger fields are not slimmed or replaced by hash references.

## Implemented source slice

The family-local adapter factors the existing whole rebuild into a private
bounded-output primitive. The existing public `rebuild_f36_notes_trials_v1`
still evaluates and returns the whole list through the same financial code.
The new `iter_rebuild_f36_notes_trials_v1` emits every original slot in order
without changing `documents_requested`, topology, corpus identity or ordinals.
It uses a fresh `NotesSource` for each document, retaining the full corpus and
the existing ORIGINAL loader, while sharing the caller's actual read counters.
This bounds bridge caches, evaluations, inventories
and classifications to one document. Annual policy is freshly captured for the
one current requested document. Callers should supply PRIMARY contexts before
whole-corpus annual captures; retaining such a prebuilt capture outside this API
would itself consume memory.

The existing validator's financial/ROOT/source/classification/retention/period/
candidate/mapping checks are factored into one private per-document primitive.
The old public whole-list validator still checks the complete query frontier
and returns its original whole-list canonical clone. The new single-document
validator establishes only that one slot's consistency, never completeness.

`gemini_json_f36_notes_stream_v1.py` exhausts an iterable against the FULL declared
source axis. It rejects missing, duplicate, extra, reordered or foreign trials,
reuses the financial validator, and writes an exclusive scratch array. It retains
small ordered trial offsets, one-LF hashes, query frontier and metrics. It hashes
the sweep material with its `sweep_id` absent, then streams the same sorted JSON
keys with that ID present. The material and canonical sweep domain have one LF;
the stored-sweep representation has exactly two. Array elements remove exactly
one known terminal LF, never arbitrary whitespace. Non-ASCII strings, integer
precision, null, blank, dash and all source fields use the existing serializer.

Compiled controls and optional expected query are snapshotted before iteration;
late caller mutations fail closed. The array and final sweep stay open through full hash/path/six-field identity
checks before and after streaming. Scratch must be new, outside Git and the
declared source authority. Outputs never overwrite older files. Partial scratch
files remain on failure; no COMPLETE marker or database is created. Per-trial
64 MiB and per-file below-2-GiB limits are declared byte ceilings, not proof of
process RAM fit. Serialization and financial validation still allocate within
one document; the largest document must be measured under the owner lease.

The proposed-run ID helper uses the old store's sorted unique implementation
reference axis and exact content domains. It is a pure declaration/codec helper,
not an authenticated stored-run receipt.

## Planned validation, not results

The new synthetic source file contains a two-original-slot FULL/COMPACT golden
with an explicit outside-request trial. It compares old whole-list sweep bytes,
candidate/query/sweep IDs, independent old-store run-ID grammar and precise trial
offsets. Missing/duplicate/reordered/extra/boolean ordinal, resealed financial
tamper, query-frontier drift, late compiled-input drift, earlier spool corruption,
output collision, Git-root and byte-bound controls are authored.

A second group uses the existing real tiny synthetic SQLite source fixture and
PRIMARY context, with actual notes/ORIGINAL/ROOT rules and no financial or
authentication validator mocks. Full/compact and annual/interim-Q4 cases compare
the legacy monolith with the document iterator, then compare exact whole sweep
bytes. These fixture DB operations are definitions for a later root-only test
lease; they were not executed during authoring. The two-slot declarations are
explicitly structural and do not pretend to contain a second real source record.

Before a whole job: independent source review, focused old-plus-new tests and
bounded actual-document equivalence using the same full spec/axis are required.
The owner must measure largest-document peak/RSS/AS and combined SSD use under
the AS 2 GiB synthetic/development lease. No cap increase or unchanged whole retry
is authorized here.

## Required next stage: not implemented

This stage cannot persist or promote a whole run. It accepts a public iterable,
not an authenticated capability; pure ledger consistency is not fresh IO proof.
The owner must still hold/authenticate the complete source/PRIMARY/config/code/
corpus frontier and fresh source snapshot with before/after hash, identity and
SQLite sidecar/integrity guards. Iterator completion does not replace those IO
barriers. A cooperative exclusive owner lease remains required.

The next F36-local stage must perform fresh independent cold reconstruction of
every original trial, exact per-trial plus whole query/hash/metric/frontier
equality, and one-run transactional SQLite insertion. It must use exact-sized
`zeroblob`/`blobopen` chunk writes for the whole sweep and preserve all existing
normalized trial/candidate/mapping rows and hashes. Any mismatch rolls back the
new transaction, and no OFFICIAL selection is permitted by the notes prototype.

Readback must stream the stored whole BLOB and compare all normalized content,
counts, IDs and hashes without a whole `SELECT sweep_bytes` or `json.loads`.
The existing generic store/replay/loader/export APIs still require whole lists
and materialize the whole BLOB; calling them after this writer would recreate
the allocation failure. New F36 callers must use an explicitly reviewed bounded
route or fail closed. One validated persisted trial can then feed the existing
pure F36 workbook projector, with strict typed readback and complete evidence.

Those streamed SQLite, normalized-trace, cold-replay, persisted-readback,
source/PDF/residual/legacy and financial gates are NOT IMPLEMENTED or waived by
this first stage. No shared canonical helper, generic store, frozen evaluator,
generic runner, F39, F37, integration branch or provider path is edited here.
