# F39 authenticated query-axis handoff — source-only, UNRUN

Base: `6fddfcc1f657b27381ffc1e23eaa22bad2180e4d`, owned combined F39 branch.
The prior unit/full gates do not certify this new source delta or the actual
13-document pilot. No runtime, import, AST, compile, lint, test, DB, WSL,
provider, PDF render/extraction or commit was performed by this author.

Owner publications 0496/0497 reported a pilot failure in the unchanged frozen
query-binding validator at line 13822. The immutable 0499 before-image is
`restore-receipts/F39_BINDING_BEFOREIMAGE_6FDDFCC1_CONTROLS_20261028_V1/`
`binding-beforeimage.json`, SHA-256
`d5f13955ea204e42ecf63ab3645e1a05d47540110f751eb08ddd65bfbe95f445`,
641188 bytes. Both observed controls are actually UNRESOLVED, with zero
mappings and `ALGORITHM_PRINTED_PRIMARY_ROOT_SOURCE_OWNERSHIP_UNPROVEN`.
BAB20's accepted cluster is NOTE physical37/s2/t1, while the returned private
PRIMARY candidate cites physical10/s1/t1. EIB39's accepted NOTE physical44/s1/t3
is replaced by private PRIMARY physical11/s1/t1. The early T6 return from the
note/PRIMARY merge preserved the private source evidence but lost the accepted
outer query identity. Thus the initial inference that every surviving READY
candidate had drifted was not established by the actual validator inputs.

The family-local public evaluation now explicitly hands the accepted query
context across the original-note and ordinary note/PRIMARY finalizations only
when the returned region axis differs. If the candidate already has the exact
authenticated outer axis, every status returns a byte-identical canonical
clone immediately. No PRIMARY proof is inspected or required on that path.
The outer family query, source context and original-note/PRIMARY descriptors
have already been freshly replayed before this handoff. A differing axis can
be replaced only when the candidate is the exact T6 ownership HOLD, has an
empty typed mapping list, retains the freshly selected private PRIMARY axis,
and its T6 evidence matches that PRIMARY locator and original page/table
hashes. Other drift raises an error. The original closure/evidence, status,
reason, values, types, source references, units and roles remain unchanged.
Only the component-region query identity and its normal sealed IDs change.

A context-only receipt retains both axes, the prior candidate ID, the selected
PRIMARY descriptor hash/locator and the authenticated outer query's exact
canonical UTF-8 bytes, SHA-256 and byte size. Query proofs can contain
mapping-shaped evidence, so the complete retained query is opaque canonical
JSON text rather than another active mapping object. The receipt and candidate
use their existing canonical identity algorithms. Fresh public trial replay
recreates the handoff and rejects self-resealed false evidence.

READY note/PRIMARY candidates retain their accepted NOTE axis, IDs and existing
explicit PRIMARY projection and financial proof byte for byte. They receive
no new handoff receipt or permission requirement. A printed PRIMARY root
outside the NOTE region remains existing supporting evidence, not a replacement
query region. Root's independent review removed an earlier draft requirement
that all READY candidates have a PRIMARY proof: the confirmed failure is
U-only, and unused or unsupported PRIMARY metadata must not impose a new
financial constraint on a separately authenticated candidate.

This patch deliberately retains the previously reviewed precedence: an
unusable present printed PRIMARY total holds before sign reconciliation or
registered-negative final sealing, and a valid note cannot rescue it. In the
actual T7a subset, original171/176 have this T6 reason and zero mappings;
original232 has the registered printed-dash discrepancy reason and zero
mappings. Independent NOTE-only authority and any proposed READY restoration
require separate review. No such financial-policy change is included here.

The new test module `test_gemini_json_income_tax_query_axis_handoff_v1.py`
authors thirteen cases. They build indexed evidence, adapt it, build trials,
invoke the ACTUAL frozen sweep query-binding validator and replay the family
from source. Source-shaped NOTE plus separate PRIMARY cases cover the exact
early HOLD topology and an existing signed-display READY root outside the
accepted NOTE region. The READY result must equal the existing financial route
before the new context helper byte for byte, with no new handoff receipt. A
public note-only READY case also remains byte-identical when the helper is
given unused, independently selected unresolved PRIMARY metadata. This is a
context-boundary invariance control, not a new mixed-source READY permission.
Approved original171 PRIMARY and original232 NOTE page
bytes exercise registered-negative source paths on explicitly new dense
one-page test manifests, retaining physical/source identities and raw cells.
These bounded manifests are not FULL271/COMMON204 corpus acceptance. Six
negative controls reject unrelated/private-axis/source/status/mapping drift;
two adversarial receipts receive valid fresh hashes and IDs but must fail
actual source replay. Whole held candidates and the new receipt must contribute
zero recursively recognized mappings. All new tests remain UNRUN.

Suggested guarded focused modules are the new handoff module, existing
`test_gemini_json_income_tax_printed_total_root_binding_v1.py`, and
`test_gemini_json_income_tax_printed_dash_real_profiles_v1.py`. Root may add
the source-observation contract module. The existing signed-display module is
unchanged; the new module exercises its established READY/negative source
shapes directly. Root owns capture, actual focused validation and the fresh
13-document pilot before any larger coverage or acceptance claim.

The frozen shared evaluator and generic runner remain untouched. F30 native
work in its separate owned branch remains uncommitted and unchanged by this
urgent F39 correction.
