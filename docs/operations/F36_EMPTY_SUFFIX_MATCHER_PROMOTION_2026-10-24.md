# Empty-suffix predicate promotion

After5f3e294f448485af13febe44c4a653c246b3f119, integrate the reviewed
f768cbbfd4ad3a376e29ae05d32e2f85e0e22348 change into the owned
codex/f36-operating-expense-laptop branch. Production code adds exactly two
lines to the nonfrozen hierarchy matcher: returnFalse when its already-built
suffix set is empty, before allocating constants/a nested helper. This is the
old predicate's existing False outcome; normalization, membership, suffix
construction, nonempty handling, exceptions and financial policy are unchanged.
No cache, source transformation or frozen-file change is introduced.

Committed hierarchy blob SHA:
1e1822a4931738d003a0bbf4284fc421d2b0919713f5f7ac3b3aed2baccde2a1.
New38-test blob SHA:
7105782a6b9d5227659bdd20abce5a1c12683d1342ca156b3d509da0f8aa5cd6.
Before commit, all2125 required indexed Git blobs AND modes matched the tested
f768 snapshot exactly. Git additions to the source/test axis were exactly the
reviewed two paths. Docs do not change that runtime axis.

Actual Python3.12 gates, with complete pre/post input pins, actual origins,
compile/Ruff and exact case/JUnit denominators:

| Gate | Actual result | Terminal receipt SHA |
|---|---|---|
| Literal/type/order/config focused |38normal PASS|73c3f90a57ed80f6a2837d0eca7a670548b1e05a6f432dbc7edfffd61007e7a7|
| Prior1065 + new38 |1103normal +4327sub PASS;5430declared/1103elements|504ff2a516530bf93e925a745fad39599fdca3b58a3bbfea4c0bdc35729b852f|
| F37/F39 regression |352normal PASS;352declared/elements|eaf89c3d41ad6339bf0f57bf2d57f4570d8f7edd528a356efb7c7cc918e6736f|

Every gate had zero failures/errors/skips. Broad receipt:
`/srv/bctc-receipts/f36-empty-suffix-composed-1103-v1-20261024T015600Z/REVIEWED_CASE_MANIFEST_FOCUSED_V2.json`,
5189354bytes. Cross-family receipt:
`/srv/bctc-receipts/f36-empty-suffix-cross352-v1-20261024T070800Z/REVIEWED_CASE_MANIFEST_FOCUSED_V2.json`,
1821159bytes. Reviewed case SHAs respectively
1d1155edd260babf6ba974f55e43cf6e43ff0caae40f9a2de9b582ba76726467 and
51a2c3ce6cf7a3697f1d5d1862fec9f6b0ad0619bb5e99f5c3a12dcc214c213e.

Original6 V7 source comparison passed all eight exact typed source/index/query/
trial/coverage/observation axes and retained22 raw violations. Both source/PDF243/
SQL/code/runtime/closure barriers passed. Receipt22289cc0c010b50beddb5dbcbbf54d978eb168d08ff291674ad6da4609b2c820
is recorded in the preceding checkpoint. Baseline/candidate CPU146.91/123.66s,
wall153.09/133.31s is one warm six-report panel, not a whole-corpus speed result.
Independent cold replay is NOT_PERFORMED; this optimization grants no financial
mapping, held-row declaration, family seal or canonical export authority.

Before mutation, a fresh exact186-event S3 coordination review passed with no
competing F36 owner, SHA301d3b367e17f88e8ade668a2a9936d0c28fb355f5e5a744691906e4076b5955.
AWS account037827769459/user vps_username, bucket versioning Enabled. No S3
object was overwritten or deleted. The integration branch remains base8efd.

ADMIN remains an unpromoted draft after its incomplete source comparison.
Notes88 remains separate after149unit PASS; its fresh full/common runs and
complete source-cell/disposition delta ledgers remain required. F39/F36 are
unsealed, F37 unclaimed, F41 locked; no providers or original data modifications.
