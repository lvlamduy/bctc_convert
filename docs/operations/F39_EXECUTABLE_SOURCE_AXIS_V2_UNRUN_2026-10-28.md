# F39 executable source axis V2: source-only, UNRUN

Base: `51dbb56dc3733c4f3aa9474e9bf8dbdef6fefdc0`.
Task branch: `codex/f39-source-unit-authority-v2`.

This checkpoint closes an implementation-manifest omission in the F39 runner.
It grants no financial mapping, provider, production selection or family seal.
The separately owned original-source-unit correction requires its own review
and exact combined source capture before any execution.

## Observed authority gap

The original runner recorded35 unique implementation paths. Its fixed
multitable compiler imports and calls
`accounting_family_topology_v1.compile_accounting_family_topology_spec_v1`;
that source file was absent from the recorded axis. Static review of the
runner's four script entry/import roots found30 unconditional project source
files, including six files missing from the old implementation axis:

- `evaluation/accounting_family_topology_v1.py`;
- `evaluation/gemini_json_structural_context_v1.py`;
- `storage/gemini_family_effective_page_frontier_v1.py`;
- `evaluation/gemini_json_first_batch_v1.py`;
- `evaluation/gemini_json_first_provider_v1.py`;
- `evaluation/gemini_json_region_repair_v1.py`.

The last three are already imported by the existing page-store module for
types/validation. Pinning their source does not invoke or authorize a provider.
The four package initializers for `bctc_ai`, `evaluation`, `storage` and
`source_structure` were also unlisted. Their current bodies contain only
package documentation and the root package version.

The static30-file review is a lower bound, not evidence that arbitrary dynamic
dispatch is unreachable. On the F39 path, the flat compiler/sweep and generic
store dispatch to the already declared multitable source/query/replay modules.
The store and generic runner also import the effective-frontier module even
when its optional frontier application is absent. The source change combines
an explicit declaration with reconciliation of the actual loaded process.

## Revised source contract

The family-local `_income_tax_implementation_paths_v2` centralizes the original
35-path declaration and adds those six modules and four initializers, giving45
declared paths. Existing configuration, source-context, repair, language scope,
storage, shared evaluator and shared runner references remain included.

At the beginning of `run`, before financial index/document/source work or
family compilation, `_seal_income_tax_implementation_axis_v2` records the
declared paths plus any project sources already loaded in the process. Every
such module must have an absolute `.py` origin inside the exact runner checkout,
with no symlink path or disagreement between its file and import-spec origins.
Each additional initial source is recorded with its actual SHA256 and byte
count. This preserves use inside a process that already loaded another family;
those imports do not become invisible dependencies.

The initial path/reference axis is then fixed. A declared dependency can load
later, but a new unlisted project module cannot enlarge the axis after work
has begun. Every check compares the complete file references with the original
seal. Module names already observed must retain the same pinned source and
cannot disappear or switch to another otherwise listed file. The check covers
`bctc_ai` names, known F39/generic script names, and aliases whose actual file
lies under the checkout's source package or scripts directory. Standard library,
third-party and test module files are outside this project-source definition.

Checks surround compilation, warm source evaluation, final warm PDF callbacks,
the warm persistence handoff, independent cold replay/persistence, output PDF
callbacks and export. Existing implementation-reference comparisons remain.
The bounded diagnostic and normal audit retain the final module/source map
and ordered phase check hashes/counts. These are source/origin observations,
not authentication of arbitrary in-memory Python mutations.

The authenticated cold adapter independently seals its initial declared/loaded
project axis at creation and checks it at entry, after declarative compilation,
after source-context close, after final PDF callbacks and before returning
trials. Its existing caller implementation/authority-reference checks remain
unchanged. Legacy synthetic callers with empty or deliberately small external
reference lists therefore gain the same project-source fence; those lists
cannot be used as a bypass or a substitute for the fixed project-source axis.

## Authored tests and remaining gates

The new `test_run_gemini_json_income_tax_implementation_axis_v2.py` calls the
actual family compiler and binds the compiler function's real source path;
removing it from the axis must fail. Further controls exercise initial local
other-family imports, a declared late dependency, a late unlisted module,
initial/late foreign origins, source-byte drift, a module switching between two
already pinned files, removal of a previously observed module, conflicting
file/spec origins, missing/relative/compiled-only origins and script aliases.
Synthetic source files stay inside pytest temporary directories. No raw corpus,
PDF, database or registered source fixture is rewritten by these controls.

All new source and tests are UNRUN. Independent root source review, exact
combined commit capture and a complete focused gate including the existing
runner tests are required. Subsequent source pilot, authoritative full271 and
common204, independent cold replay, observation contract, SQLite integrity,
PDF/residual audit, consumer/profile binding and ledger gates remain open.
Old5ea-pinned readers/promoters and old receipts cannot establish acceptance
for this new implementation axis. F39/F36/F37 remain unsealed and F41 locked.

Only this family-local runner, the new test module and this new operations
note belong to this change. The frozen shared evaluator and generic runner
remain read-only at their registered SHA256 pins.
