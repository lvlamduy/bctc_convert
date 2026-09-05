# F30 SERVICE_ACTIVITY exact service leaves — FINAL FREEZE / HOLD

## Freeze identity

- Branch/worktree: `codex/f30-service-leaves-vps` at
  `/dev/shm/f30-service-leaves-vps`.
- Exact base: `9a01a391dc097283ba436ef01e76ce56d42f4a5b`, selected from
  `origin/codex/f36-operating-expense-vps` after remote readback.
- Operational family number: F30 `SERVICE_ACTIVITY`; historical conceptual
  display number: Family 31.
- No commit, push, S3 write, provider call, OCR route, geometry route, or source
  DB mutation was performed.

The exact frozen tracked set is four files:

| Path | Bytes | SHA-256 |
|---|---:|---|
| `config/families/tm-service-activity-evaluation-v1.json` | 6,227 | `830a14313e4227926355c3142f9903812ed3f04cb812ccb6a141769cf78022ca` |
| `config/families/tm-service-activity-schema-binding-v1.json` | 1,868 | `620d2514f0c14c91400880b9f6309d480fd41fb25b130c79b4f92ad045bb6b5b` |
| `config/families/tm-service-activity-topology-v1.json` | 16,965 | `0778bb979393b76fe0cc6b9a6b00d85f8e460d1bd55fbe2276e8054dec217116` |
| `tests/unit/test_gemini_json_service_activity_family_v1.py` | 57,207 | `b48e30ecd2bccfcec942cbe291db4ef815bc176084144f843ff0e1b3b481f06c` |

`git diff --binary` is 24,608 bytes, SHA-256
`1c50f45ec4df03fa2b60d11975c1be26be3ac377e37124b36fc3e9ea5a6950ec`.
`git diff --check` and JSON parsing of all three changed specs pass. Ruff passes
for the F30 family test, adapter test, runner test, adapter implementation, and
specialized runner.

## TDD and focused gates

- RED before config implementation: 24 cases, 20 failed / 4 passed;
  `/dev/shm/f30-service-leaves-evidence/red-new-leaves-v2.xml`, 41,682 bytes,
  SHA `1dc30a031d4daafe4b8b4bed77234b3f3c8b34992e43444e456e103da1f52527`.
- Targeted GREEN: 22/22 selected cases;
  `/dev/shm/f30-service-leaves-evidence/green-new-leaves-v2.xml`, 5,377 bytes,
  SHA `19dab37ae69bc6954341219f91e722466b9d3ef27b5a8e5bed6749d73f00add3`.
- Final combined F30 family/adapter/runner gate: 137/137 PASS in 5.34s;
  `/dev/shm/f30-service-leaves-evidence/FINAL-focused-three.xml`, 27,842
  bytes, SHA
  `9ffb55895fc7c799221a534103050a0b8033e760447bd1d552b761dd2aacee46`.

The family-local change maps only exact aliases under `INCOME_PARENT`, splits
fund management from trust/agency, splits remittance from payment, projects the
already authenticated custody/rent validation role into RNID1162, and changes
the no-left-behind policy so an unknown direct money row anywhere in the
selected service population cannot be silently dropped. Broad labels remain
unmapped and force typed U; wrong-owner and outside-owner cases fail closed.

## Governed full271 result

The authenticated full271 runner completed successfully against manifest index
SHA `969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`
and source DB SHA
`ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`.

- Baseline: 202 READY / 68 NOT_OBSERVED / 1 UNRESOLVED, 2,150 mappings.
- Frozen patch: 202 READY / 68 NOT_OBSERVED / 1 UNRESOLVED, 2,194 mappings.
- Delta: exactly +44 mappings across exactly 44 READY documents:
  +34 RNID1162 from 37 distinct custody/rent source rows, +8 RNID1161 fund
  management, +2 RNID1165 remittance.
- All 271 statuses are stable. The other 226 documents have byte-identical
  status, reasons, and mappings. NAB92 remains the sole U and only adds the
  expected custody duplicate/conflict reasons; it gains no final mapping.
- Every old trust/agency lane equals new trust/agency + fund management; every
  old payment lane equals new payment + remittance. The old source frontier is
  exactly partitioned. Custody/rent refs equal the distinct prior authenticated
  source-only frontier, and no valuation/debt row is absorbed.
- Source-observation contract reports PASS/0 violations over 4,388 mapping
  lanes and 8,776 cells.

Artifacts:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `/dev/shm/f30-service-leaves-full271-v1/sweep.json` | 56,546,822 | `0f640347546293a62b15c0a0961138ba99e351fdee81a12e2061b4b2f023aacc` |
| `/dev/shm/f30-service-leaves-full271-v1/sweep.audit.json` | 5,302,811 | `f1e8c06060c169049e50e0e7555edae7954918fb79a38766e1d942d3087f5bc4` |
| `/dev/shm/f30-service-leaves-full271-v1/results.sqlite3` | 107,638,784 | `4097cf675783cdb9a4fbffc63adf59257e7fd96c443632cca8de39f6baf2c075` |

The results DB passes immutable read-only `quick_check=ok` and an empty
`foreign_key_check`; it contains 1 run, 271 trials, 2,194 mappings and 1 export.
Machine-readable delta:
`/dev/shm/f30-service-leaves-evidence/FULL271_DELTA_RECEIPT.json`.

## PDF-visible evidence

Five source pages were personally viewed from the current PDFs:

- KLB53 p28, source SHA `66e07ea5...8da2`, render SHA
  `b997e591...7691`: rent is separate from valuation.
- NAB93 p58, source SHA `67303850...9286`, render SHA
  `e15b4ac8...ef5`: rental and custody are distinct siblings that RNID1162
  intentionally combines.
- SHB162 p45, source SHA `7cdc3794...0d50`, render SHA
  `b6c5700d...bd33`: exact custody/safe-deposit rental child.
- STB199 p68, source SHA `522e5189...1dd`, render SHA
  `cdb19201...959`: remittance is separate from payment/card service.
- TCB215 p72, source SHA `553195cd...527`, render SHA
  `05f92f6f...c7cb`: fund management is separate from trust/agency.

## Binding release HOLD

The leaf semantics and full271 delta pass, but the frozen shared provenance path
still repeats each row-level source ref once per lane. The 44 new mappings carry
94 refs but only 47 distinct refs: custody 74/37, fund 16/8, remittance 4/2.
This is 47 exact duplicate refs and is a binding terminal HOLD.

The proposed external regression is frozen outside the worktree at
`/dev/shm/f30-service-leaves-evidence/test_f30_new_role_source_ref_uniqueness.py`
(1,122 bytes, SHA
`d9e86169b3c63d3f3efd8d9dee34f8c00911938afb4e04e75e711ebb4f85a048`).
It is intentionally RED 3/3 on the current shared code; JUnit
`EXPECTED-RED-source-ref-uniqueness.xml` is 13,340 bytes, SHA
`ffefd1861fdfd20331b3ebb004dac9a094451eef18a430923b0bf4395db76465`.

Do not commit/push/checkpoint this F30 work as terminal. After the independently
reviewed shared source-ref identity fix is authoritative, rebase/cherry-pick it,
require the external uniqueness gate to become GREEN with zero duplicates, and
rerun governed full271 once before release review.
