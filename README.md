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



## Safety invariants

- Never modify a source PDF, schema workbook, or template in place.
- Never turn a blank or dash into zero.
- Never synthesize a value to make an accounting equation balance.
- Never call a value high confidence without cell-level geometry and
  independent numeric agreement.
- Never use Role A output during a frozen Role B evaluation.
- Never reuse, reorder, or delete an existing schema ID.
