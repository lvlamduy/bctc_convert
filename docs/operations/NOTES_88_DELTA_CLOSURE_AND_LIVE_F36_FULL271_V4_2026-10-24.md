# Complete notes delta closure and the live F36 FULL271 diagnostic

This follows15d1b29d96d41c048038e3e61280a4d1ace80fe4. Production source remains
the tested matcher change fromf74bd7f8. The notes88 engine is still a separate
experimental branch; F39/F36 unsealed, F37 unclaimed, F41 locked. No providers,
original-source writes, new extraction or family seal.

## Actual complete derived-ledger comparisons

The narrow V4 SQLite binding succeeded on the actual stores: verified bytes
were privately deserialized, query_only enabled, and serialize-byte equality
checked before/after quick_check/FK/SELECT. All four original input paths were
rehashed with byte counts and no-sidecar checks at exit. No original-path
held-FD claim is made. Keep the prior actual V3 sealed-memfd failure unchanged.

Both comparisons are PASS_DIAGNOSTIC, correct404/88 heads/corpus/PRIMARY profiles,
stable inputs, zero identity problems, zero unverified cells and zero invalid
source tables. Every accepted cell is full typed-record identical. The complete
changed/one-side/unlocated/multiple occurrence contract, not sample counts,
was used; no occurrence was silently overwritten.

| Corpus | Removed HOLD observations | Changed HOLD to HOLD | Wall | Peak KiB |
|---|---:|---:|---:|---:|
| FULL271 |184 =6F37 +178DEPOSITS|40|8.40s|716656|
| COMMON204 |160 =4F37 +156DEPOSITS|28|6.65s|542772|

No accepted observation changed or disappeared. Changed HOLD fields are only
concept/write_key/hold_reasons; raw numeric, period and unit fields are unchanged.
These conclusions concern the paired experimental outputs, not final financial
acceptance or a new audit of every original PDF.

FULL comparison directory:
`/home/bctc/notes-compare/delta-ledger-v4-full271-404-88f5-20261024T081330Z/`.
Terminal49878baf909097198f3819c03e31099f126cbb6cf432b6be6428389c0ade3b49;
summary405dcae4f5d7f93a4d5511c08f1b29adee4914c8918ae31bf3696285e7dae66b;
cells095a3912959390bf67ccdbab79cd663f3eaea15065a2d1e0a7a2d3c7147fde40,
431351bytes; dispositions609b9a742deeabbc3394720c4dd3d20172836848ad4a5f9e0723a1eef5916d2d,
287335bytes.

COMMON directory:
`/home/bctc/notes-compare/delta-ledger-v4-common204-404-88f5-20261024T082121Z/`.
Terminale21dae12f5b8c9357eedf8be8c5e5bf9ff71b5710878e560c91daf5da522d48b;
summary4df9da2f4e6e74d600d7f866be2f3fdd93046eb956181d2e7e5fdb6ae7dab284;
cellsb7fcceb089845afd2ec463e038c18e3ca5c0c295994de0e5fa5a463eb21ddaa9,
353856bytes; dispositions6fa99aa4f8e05529f98e9199bde280fc6f2306113fad8dbcbcbdf551b2308a78,
249411bytes.

A separate bounded closed-ledger audit joined EVERY removed observation to
its own newly REJECTED table. F37 removals match OWN_TABLE_IS_A_POSITION_SCHEDULE;
DEPOSITS removals match OWNER_IS_RELATED_PARTY_TRANSACTIONS. No unexpected group
or unverified occurrence occurred. Receipt:
`/srv/bctc-receipts/NOTES88_CLOSED_DELTA_REMOVAL_CLOSURE_AUDIT_20261024_V1.json`,
SHAa1b3374ec0fef487d2243c807089af4e00ffdaa2754d7454c585fbb9aa031efd,
2207bytes. This is derived-ledger closure, not fresh ORIGINAL authentication.

## Annual-policy candidates remain unapproved and unrun

The actual LPB95-page ORIGINAL discovery and two-page PDF view are in the prior
checkpoint. They do not activate a period or unit. Separate candidate7aebf0a6
was statically reviewed and is UNRUN/NO-GO: consumer trusts status-only/foreign
policy; prefix grammar can discard explicit multi-year bounds; owner/scope
and nested foreign ownership are not proven; SQL prefilter can omit a conflicting
uppercase/wrapped policy; unsupported qualifiers disappear; document selection
is applied after collector IO. A relative-header test also contradicts the old
explicit-RANGE route. Preserve this candidate and exchange0254.

Additive candidate590b27d6 fixes several boundaries but remains UNRUN/NO-GO:
physical wraps can hide conflicting/qualified policy, assertion subsets can be
resealed without a complete narrative census, and raw combining marks can vanish
before classification. Exchange0258 records these concrete remaining issues.
Candidate9801e909 adds an ORIGINAL-page capture and wrap/raw-mark handling.
Static review found one remaining source-driven NO-GO: the broad enumerated
heading rule can erase a first-year exception or foreign-owner context before
matching the calendar clause. Exchange0260 requests a finite neutral-heading
rule and two negatives. Exchange0261 clarifies that the actual runner consumes
a fresh authenticated collector capture, with no capture-deserialization path;
a new issuer registry is not required. Its planned177 tests are not actual test
results. No candidate is integrated or used for main financial behavior.

## F36 legacy FULL271 V4 is now LIVE

Root launched the independently reviewed changed/tested-code diagnostic AFTER
the short notes pair, complete ledgers, closure and policy discovery/PDF checks.
This supersedes only the earlier UNRUN scheduling state; no old failure is erased.

Run directory:
`/srv/bctc-receipts/f36-full271-empty-suffix-v4-20261024T083500Z/`.
Actual exec session22643. Wrapper01488c1982aaf7b22d94d82f730b790033f522073334b7d821d84bac8f260811,
22470bytes, at restore-tools/drafts/run_f36_full271_bounded_existing_producer_v4.py.
Private clean regular read-only runtime:
`/srv/bctc-receipts/f36-full271-empty-suffix-runtime-20261024/repo`,
HEADf74bd7f803af6f94a5ff9df2457109fe3c187ed3, owned F36 branch. All2125 code/
config/script/test authority bytes match testedf768, with actual1103normal/
4327sub and352cross-family PASS. Two frozen SHA/modes remain unchanged.

At initial inspection wrapperPID462140; owned time/process group462337 and
producer PythonPID462338. Use the process JSON and actual command/start identity,
not a bare stale PID, for any stop. Wrapper TERM stops/reaps only its owned
group and attempts the final source barrier; preserve all partial outputs.

Initial source-before.json PASS: index969ff5f8/422971bytes, DB ea9dec62/
573145088bytes, no sidecars,542 document refs checked without mismatch. This is
a FILE/REFERENCE barrier, not fresh SQL PRAGMA integrity or final replay output.
At that inspection no diagnostic terminal/new READY/U/mapping counts existed.

Same budgets as V3: AS5GiB, producer CPU6600soft/6900hard, producerwall7200,
source barriers300each, nice19, TERM/KILL20. Root outer supervisor8100+330
allows wrapper cleanup; it does not increase the producer budget. Prior V3
CPU-limit FAIL26c5add remains retained. No automatic retry or cap increase.

Poll actual session22643 to terminal and read execution-result.json. Only the
terminal can establish DIAGNOSTIC_COMPLETE_NOT_RELEASE or a retained FAIL.
No store/residual registration, final PDF audit, fresh SQL closeout, COMMON
legacy diagnostic, family ledger or seal is supplied by this running job.

While it lives: no other source/SQL/tests/corpus/profiler/comparator/data-reading
jobs. Native Git/AWS/static code/metadata and additive drafts may proceed; keep
all pinned snapshots/inputs unchanged. Do not open F41 or invent counts while
waiting. New proof artifacts remain LOCAL_ONLY unless separately S3-published.

Before this documentation mutation, a fresh read of all187 exact event versions
found no competing F36 owner. AWS identity/versioning passed. Receipt:
`D:/bctc_bank/restore-receipts/f36-pre-promotion-coordination-20261024T091452115529Z-7b5eda3805e54fcba18f7d9843d7a593/F36_PRE_PROMOTION_COORDINATION_REVIEW_V1.json`,
SHA1c2ec4e62aa60b58f3d49c4b2a2b026d05ebd38ad2e08e8f4377b75f8b502c8e.
This was read-only and did not publish artifacts or a terminal event.
