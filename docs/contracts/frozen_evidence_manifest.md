# Frozen evaluation evidence manifest

Every artifact presented to a frozen/calibration process is typed. A path label alone is not authority.

## Stages

- `PAIR_REGISTRATION`: may see the paired source identities and pairing config. The page matcher uses pixels/order only and cannot read text or values.
- `ROLE_A_BUILD`: may read only the reference-side PDF and its declared OCR/layout/schema/config evidence.
- `ROLE_B_READ`: may read only the candidate-side scan/render, preprocessing artifacts, pinned model, and inference config.
- `ROLE_B_MAPPING`: may read Role B OCR/layout plus schema/hierarchy/config. Role A and historical values are forbidden.
- `ROLE_B_POST_MAPPING_VALIDATION`: may read an already-resolved Role B record and resolved-ID-only historical weak reference. History can trigger reread/review only.
- `COMPARE`: may read sealed Role A and Role B results after both are complete.

## Fail-closed invariants

- Role B paths containing a machine-reference, Role A result, or prior comparison are rejected even if mislabeled with another evidence kind.
- Historical evidence is rejected during mapping and candidate generation.
- A Role B seal requires a clean preprocessing Git revision and revalidates render, inference output, metrics, package freeze, config, model revision/weights, and sealing-code hashes.
- Seals are append-only for a run. Existing seals are never overwritten.
- Agreement has `NO_PROMOTION` confidence effect. Missing rows, invalid/multi-number cells, value/state disagreements, note disagreements, and label disagreements route to explicit reread/review classes.
- Searchable/native Role A is still a machine reference, not human gold. It cannot prove schema/full-tuple or production accuracy.

The executable policy is in `src/bctc_ai/evaluation/frozen_suite.py`; sealing is in `src/bctc_ai/evaluation/sealing.py`.
