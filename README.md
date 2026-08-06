# bctc-ai

`bctc-ai` converts Vietnamese bank financial-report PDFs into traceable Excel
workbooks backed by the supplied append-only schema.

The project is being rebuilt from a clean implementation. The source PDF is
always authoritative. OCR, language models, MongoDB history, and accounting
equations are supporting evidence only; uncertain values fail closed into the
review or unresolved queues.

## Bootstrap

```bash
python -m venv .venv
.venv/bin/python -m pip install uv
.venv/bin/uv sync --frozen
.venv/bin/bctc-ai audit
```

The bootstrap audit writes immutable source identities under
`data/registered/`, imports the four supplied schema workbooks, refreshes the
required audit documents, and reports whether a verified off-machine backup is
available.

See [PROJECT_GOAL.md](PROJECT_GOAL.md), [ARCHITECTURE.md](ARCHITECTURE.md), and
[ACCURACY_REQUIREMENTS.md](ACCURACY_REQUIREMENTS.md) before running a production
document. Recovery procedures are in
[BACKUP_AND_RESTORE_RUNBOOK.md](BACKUP_AND_RESTORE_RUNBOOK.md).
The durable strategy, clarification, result, and change index is
[PROJECT_MEMORY.md](PROJECT_MEMORY.md).
Server reconstruction is documented in
[docs/environment/SERVER_REBUILD.md](docs/environment/SERVER_REBUILD.md); the
isolated Blackwell/PaddleOCR-VL setup and its retained failure history are in
[docs/environment/GPU_RUNTIME_RUNBOOK.md](docs/environment/GPU_RUNTIME_RUNBOOK.md).
Crash-safe multi-page PP-OCRv6 execution, exact parameters, and server-transfer
rules are in
[docs/environment/BATCH_OCR_RUNBOOK.md](docs/environment/BATCH_OCR_RUNBOOK.md).
The general, order/hierarchy-based statement and row-mapping design is in
[docs/STATEMENT_LOCATION_AND_MAPPING_STRATEGY.md](docs/STATEMENT_LOCATION_AND_MAPPING_STRATEGY.md),
with executable boundary/recovery commands in
[docs/environment/STATEMENT_LOCATION_RUNBOOK.md](docs/environment/STATEMENT_LOCATION_RUNBOOK.md).
The general multi-table, variable-column Role B parser, Role C row/axis
reconstruction, and order-only fusion safety rules are in
[docs/STRUCTURAL_READER_FUSION_STRATEGY.md](docs/STRUCTURAL_READER_FUSION_STRATEGY.md).
The first sealed six-page scan/searchable calibration and its migration-safe
replay procedure are in
[docs/experiments/E-0010-REPLAY.md](docs/experiments/E-0010-REPLAY.md).
The independent PP-OCRv6 geometry recovery, exact hashes, and server replay
procedure are in
[docs/experiments/E-0011-REPLAY.md](docs/experiments/E-0011-REPLAY.md).
The clean batch/checkpoint equivalence and seal regression is in
[docs/experiments/E-0012-REPLAY.md](docs/experiments/E-0012-REPLAY.md).
The clean MBB/VCB ordered statement-location and scope-exclusion calibration is
in [docs/experiments/E-0013-REPLAY.md](docs/experiments/E-0013-REPLAY.md).
The independently sealed 200-DPI MBB/VCB Role B and Role C acquisition, exact
settings, retained failures, and migration-safe replay are in
[docs/experiments/E-0014-REPLAY.md](docs/experiments/E-0014-REPLAY.md).
The allowlisted, non-authoritative Mongo/DuckDB reference and rebuild procedure
are in
[docs/environment/HISTORICAL_REFERENCE_RUNBOOK.md](docs/environment/HISTORICAL_REFERENCE_RUNBOOK.md).



## Safety invariants

- Never modify a source PDF, schema workbook, or template in place.
- Never turn a blank or dash into zero.
- Never synthesize a value to make an accounting equation balance.
- Never call a value high confidence without cell-level geometry and
  independent numeric agreement.
- Never use Role A output during a frozen Role B evaluation.
- Never reuse, reorder, or delete an existing schema ID.
