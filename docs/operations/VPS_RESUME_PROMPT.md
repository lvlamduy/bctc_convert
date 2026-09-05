# Resume prompt for Codex on the new machine

Read `docs/operations/VPS_HANDOFF_2026-09-05.md` first and follow it as the
restart authority. Work only in 2025-through-current scope. Restore/verify the
immutable S3 migration checkpoint before code mutation. Fetch all remotes and
do not merge any `wip/*` commit merely because it is pushed.

Start by independently reviewing branch `codex/shared-source-ref-unique-vps`
at `b6cfdc53a21b36bf03503d02e67f30e810152261`. Its stable exact-source-ref
normalization must remain limited to the two documented producer origins, and
the global contract must reject any survivor. Then run the staged common204 and
full271 provenance replays with additive identity-translation receipts.

Only after that rebase `codex/f30-service-leaves-vps` (`6a620717...`), make its
three expected uniqueness regressions green, replay full271 and request an
independent F30 release review. Do not call Gemini/provider, do not use OCR or
geometry stacks, do not repin common204 prompt metadata, and do not open F41
before F36/F37/F39 terminal acceptance.
