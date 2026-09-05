# Family 36 semantic-period and source-repair checkpoint — 2026-09-05

This is an additive preparation checkpoint for `OPERATING_EXPENSE`. It is not
a family release, a full-corpus result, or authority to reuse an old diagnostic.
The active scope is reports from 2025 through current. No provider call was
made while producing this checkpoint.

## Git scope and ownership

- Base: `codex/27-bank-2025-current` at
  `8efd618b6c77f0cdbb402a440e7ba3b3549184f1`.
- Worker: `codex/f36-operating-expense-vps`; last pushed parent before this
  checkpoint was `a715e840c0e2516a2dfaa0a1c273b574b80f09e5`.
- F36 is VPS-owned. F39 remains laptop-reserved. F37 remains read-only on the
  VPS until the laptop explicitly acknowledges the exact additive ownership
  proposal. Family 41 remains closed until F36, F37, and F39 are terminal.
- The shared evaluator and shared runner remain byte-frozen at, respectively,
  `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`
  and `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.

## Algorithm changes in this checkpoint

The family-local continuation path now proves a semantic/physical two-lane
bijection before combining adjacent pages. Explicit receiver headers must agree
with the sender's exact source lane keys, dates, duration counts, cumulative
qualifier, and quarter number. Reversed physical columns are reordered only on
a private clone; source references are mapped back to their original physical
ordinals. Blank continuation headers may inherit physical positions only from a
complete sender axis.

A comparison-only frontier retains source information that the shared bare-year
axis does not express. Within its bounded header grammar, it validates real
calendar dates, masks complete date tokens before looking for month counts,
recognizes governed counts from one to twelve, and rejects invalid, signed,
fractional, out-of-range, overlong, or conflicting count/date evidence. In
particular, `2 tháng` and `5 tháng` cannot be treated as equal; `31/02` cannot
fall back to a bare year; and `- 2 tháng` or Unicode-minus variants cannot
silently become unsigned `2 tháng`.

Visible internal-owner continuations whose period evidence conflicts are kept
as typed `UNRESOLVED` evidence with source-bound rejection receipts. Indexed
evidence and trial replay reconstruct those receipts independently. No rule
routes on a bank name or a hard-coded document/page locator. Physical page
adjacency and exact source locators remain authenticated source evidence. No
rule uses source values, value magnitude, or a blank-to-zero inference.

Five additional null cells were authenticated against visible PDF dash glyphs
and registered as exact source repairs. The pre-existing PGB page-40 repair had
a metadata-only receipt error: its historical hash was the SHA-256 of the
official canonical JSON with the final LF removed. The family-local record now
uses the official 685-byte canonical receipt hash, reseals the repair identity
and repair axis, and preserves the historical failed gate as failed evidence.
PDF, PNG, crop, locator, selected JSON, and the raw `-单` cell are unchanged.

## Frozen candidate bytes

| File | SHA-256 |
| --- | --- |
| `src/bctc_ai/evaluation/gemini_json_operating_expense_family_v1.py` | `fb1cec140d61f6c41638b929c1fe6da256599157681276d0590de39604009cb0` |
| `tests/unit/test_gemini_json_operating_expense_family_v1.py` | `0e72cedbb27812fc02fc2b1fe9ba3662024bab805e0e0f7e17a1e1ca2d1054f6` |
| `config/families/tm-operating-expense-source-repair-v1.json` | `fc7ede97147cea1b4f98f72a7d8378535a2851e1fc896b614e687102949d4820` |
| `docs/experiments/staging/family-36-pgb-render-receipt-metadata-correction-v1.json` | `4534dd05470caf7d4377ee5ee31d2aaaff55eda57a987dfb87f1cf898609944d` |
| `tests/fixtures/f36-pgb-p040-render-receipt.canonical.json` | `d12d81ec0e4545aaaddb9c0ceb174cad8d6a1a43a877cee9d5ef04d3dec37868` |
| `tests/unit/test_f36_five_observed_dash_repairs_v1.py` | `eee1b6f42244d0e0cf903ec5182e4d22a3a6c140fccc184d01ec4aec88ff5322` |

## Verification completed

- Root Python 3.12 combined gate: 644 tests across the F36 evaluator, runner,
  portable diagnostic/coverage builders, coordination, frozen shared modules,
  and the new repair suite; zero failures, errors, or skips in 83.857 seconds.
  JUnit SHA-256:
  `dab1f21f46bea21a960b73a7c58f5fdd15634789ed536f80c081c44245caeee8`.
- Independent semantic review: 387 focused plus 85 external boundary, calendar,
  count, replay, provenance, and formerly failing spaced-sign cases passed.
  Report SHA-256:
  `602211544db73ae8a46092eb8d4dd285f3ef3e2ac75e1fee2bca848487830e38`.
  The earlier `84b3...` HOLD report and red sign-boundary evidence remain intact.
- Independent PGB/source-auth review personally rerendered and viewed the PDF
  page and crop. Full271 authenticated 20/20 repairs; common204 authenticated
  17 applicable repairs and typed three as out-of-corpus. Report SHA-256:
  `6269248198aba5c864ebdd221a9d108280597c180c692782defa13c34b8da07f`.
- Writer whole-20 actual-source witness SHA-256:
  `ed938256f4208f7ed575ae60f304165d98dfadf53796b9f5f1e9d58d97933675`.
- Fresh input preflight rehashed all 271 unique PDFs, both immutable manifest
  indexes, and both corpus databases; SQLite `quick_check` returned `ok`,
  foreign keys were empty, and sidecars were absent. Report SHA-256:
  `c906e96afc9615cc604a9863902c2e37de2769a0a1a2db3490d7956b6bf44df9`.
- Python compilation, Ruff with cache disabled, JSON parsing, Git diff check,
  and the two frozen shared-file hashes passed after the 644-test run.

The active local PDF authority remains exactly 1,013 PDFs totaling
8,405,358,934 logical bytes. It is still required for human/source
authentication and must not be deleted before the remaining family gates.

## Coordination checkpoint

The latest VPS heartbeat was uploaded as a new immutable S3 object, not an
overwrite:

- key:
  `bctc-ai/coordination/2025-current/v1/events/20260905-f36-vps-f39-laptop/20260905T085544Z-vps-f36-active-f37-ack-pending.json`;
- VersionId: `D3.1_Wf9NXEadK818eyX73k3OJGtosig`;
- SHA-256: `ba66ef5663f71f024ff71b283f514d63782e7dc23444d1e8dea619d76f1f54bd`.

At that checkpoint the laptop had not acknowledged either the exact F37
ownership proposal or the additive current-11 metadata correction. Absence of
an ACK is not permission to mutate F37.

## Remaining mandatory gates

1. Commit and push these exact bytes on the F36 worker branch, then verify the
   remote head and frozen file hashes.
2. Build a clean detached code snapshot from that commit. Run fresh full271 and
   common204 diagnostics independently; do not promote or edit the historical
   failed diagnostic.
3. Rebuild coverage and residual inputs from each new diagnostic. Explain every
   status/mapping delta from selected source and personally review every
   remaining PDF-visible violation or candidate.
4. Materialize fresh full271/common204 audit specs and authoritative family
   runs into new SQLite stores. Verify content IDs, observation coverage,
   exact common204 projection, `quick_check`, foreign keys, and tamper gates.
5. Record genuine source ambiguity as `UNRESOLVED`; never backsolve, infer a
   blank as zero, infer period/unit from magnitude, or double-count a parent and
   its children. Only complete disjoint components may create a derived total,
   with explicit derived-versus-printed provenance. A family declaration of
   `REQUIRED_SOURCE_VISIBLE_EXACT_ROOT` still requires its printed root: a
   derived sum must never replace that missing source authority.
6. Write the final full271 visual-audit ledger and an immutable S3 checkpoint
   before declaring F36 terminal.
