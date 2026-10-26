# Closed F40 source replay profile for TM Excel — V2

**UNRUN implementation checkpoint.** No actual restored database/SQL, PDF,
provider or workbook job, project import, AST/compile, lint or test was executed
by the author. The coordinator owns the synthetic test lease; Claude owns real
data execution. The previously pushed V1 branch remains unchanged.

This branch starts at `0bcf8bbfe0ef37392064e1d79a4f5cc03b132b81`. AGENTS was
read; the five mandatory operating/migration documents are unchanged from the
fully read migration-base versions. Frozen files, F40 family source/configs,
schema/template, selection store and F37 source are unchanged.

## Request and entry points

The legacy V1 public functions and strict request fields retain generic MTH
replay. They accept no new profile fields and make no family-specific fallback.
Internal source-replay dispatch and post-authentication export stages are shared
privately; neither public V1 nor V2 export accepts an authenticated bundle or a
caller callback as a substitute for admission.

V2 lives in `bctc_ai.export.gemini_tm_family_replay_profiles_v2`:

```text
authenticate_family_store_run_v2(request) -> authenticated bundle
export_tm_family_store_document_v2(*, request) -> exclusive linked export
```

V2 requires every V1 field plus exactly:

```text
request_format_version = GEMINI_TM_FAMILY_REPLAY_REQUEST_V2
source_replay_profile = F40_CASH_EQUIVALENTS_FULL_RESIDUAL_REPLAY_V1
source_replay_runner_ref = exact approved relative path/SHA/bytes reference
```

Only `CASH_EQUIVALENTS` with explicitly requested `EXPERIMENTAL` execution is
supported: the approved historical F40 runner persisted that kind. Current
selection remains an explicit separately checked policy; no selection is
assumed. Wrong/missing/unknown format/profile/family/runner or an extra plugin
field fails. `F37_CREDIT_RISK_PROVISION_EXPENSE_REPLAY_V1` is explicitly
UNSUPPORTED pending actual7b producer metadata and a reviewed fresh combined
producer/consumer checkout. No F37 import or source change is implemented.

Product CLI, not a current job instruction:

```text
PYTHONPATH=src python3.12 -X pycache_prefix=<fresh-external-cache> scripts/export_gemini_tm_family_workbook_v2.py --request <absolute-reviewed-V2.json> --request-sha256 <actual64hex> --request-size-bytes <actualbytes>
```

There is no runnable real-data request bundled here. Claude still needs exact
restored physical roots, original stored axis/run metadata and one original
READY document with full source PDF/page/date/unit/direct-row evidence.

## F40 authority and full source replay

The closed profile pins the exact source-declared 15-file producer axis at base
8efd, including specialized runner, F40 adapter, both frozen generic files,
topology/page-render/flat/observation/store/page modules, three F40 specs,
registered source repairs and the full271 residual config. The residual config's
presence in this axis is not a claim that its PDF residual gate was rerun.
COMMON204's different residual-config axis is unsupported by this initial
profile. Metadata from the actual stored run has not been inspected by the
author; these are approved expected pins, never invented database evidence.

Before importing the specialized runner, the request axis and actual stored
`implementation_refs_json` must equal the approved ordered canonical 15 refs
**byte for byte**. Actual files are hash/byte checked. V1's existing four loaded
producer-origin checks remain intact. Producer root and current bridge/profile
root must resolve to one combined checkout. The fixed source importer cannot
take a module/path/function name from the request; a foreign cached generic
runner is rejected, not hot-switched. The approved runner performs its original
fixed-root import setup. Named F40/generic/source helper origins and the loaded
runner's own declared axis are checked before invoking financial/source code.

The original entire corpus index and selected source DB frontier are
authenticated by the existing base mechanism. No subset or renumbered target
axis is substituted. The F40 profile binds the approved registered repair spec,
queries/loads complete selected source pages and calls the runner's real
`_authenticate_source_repairs_v1`: every applicable registered repair must bind
its source/PDF bytes, before-null JSON cell, physical page and exact 300-DPI
render/crop evidence. No glyph inference/OCR/provider is added. All applicable
repair PDF refs are retained for the final before-publication byte barrier,
even when they belong to documents other than the chosen ordinary target.

The warm page map is released before calling the producer's exact
`replay_cash_equivalents_trials_from_source_v1`. Its own query-evidence check and
the wrapper's exact full-original-trial comparison must pass. Counts/ordinals,
run/sweep IDs and canonical trace bytes remain unchanged. The stored READY flag,
successful callback return or one matching target document alone cannot pass.

Only then does the unchanged V1 source grammar project the chosen document.
Every mapping lane must still bind its raw selected-JSON text, period/unit,
RNID and one-to-one columns. A repaired/projected target that cannot satisfy
that strict grammar remains unsupported; the profile does not bypass or broaden
projection. Blank, dash, integer precision, duplicates, complete dated periods,
typed XLSX readback, final DB sidecar checks and exclusive external publication
retain their V1 rules. V2 request controls, profile/runner identity, complete
trial and registered-repair axis hashes and extra input refs are linked in
provenance and reauthenticated before success.

The profile does not rerun or certify all N/U PDF residual audits, seal a family,
promote to OFFICIAL, modify SQLite/source/S3, or claim financial acceptance.
The separate full transitive consumer/environment manifest remains a design
under review; the historical 15-file producer axis is not rewritten to claim a
stronger past proof. A fresh trusted clean Python3.12 process is required.

## Synthetic verification plan

The existing tiny source/store fixture gains an opt-in F40 route; default V1
fixtures stay unchanged. New tests use real source ingestion, manifest/index,
F40 query adaptation/candidate evaluation, byte-checked family callback store
ingest, full source replay and pinned template. A narrative-owner recovery shape
from existing F40 unit fixtures proves the specialized route, and generic
fallback must fail. Synthetic PDF bytes never match the historical repair
registry, so happy-path tests execute the real repair authenticator with zero
applicable repairs and perform no actual PDF render. This does not prove a
nonempty registered PDF-repair render axis; Claude's bounded real proof owns it.

Other controls reject malformed profiles before file access, F37/foreign roots,
wrong/reordered/extra/missing/noncanonical producer refs, replaced warm/cold
callable origins and cold replay omission/duplication/ordinal/value faults.
Negative loader seams are explicitly fault injection after real cold replay;
they are not successful authentication substitutes. The complete old V1
synthetic/publication/canonical suites must also be rerun by the coordinator on
this exact descendant before any push or data proof.

Whole-page source replay and repeated DB hashing remain expensive. Releasing
the extra warm map avoids retaining two complete maps, but actual peak RAM/time
is unmeasured and the old 85-test 2-GiB result is not a real F40 capacity proof.
The external authenticated-session proposal is separate, unimplemented work.
