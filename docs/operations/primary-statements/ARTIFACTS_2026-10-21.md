# PRIMARY statements — immutable S3 artifacts

Bucket `test-s3-duylv` (us-east-1, versioning Enabled), account 037827769459.
Every object was written with a new key, `IfNoneMatch: *`, a SHA-256 checksum
and exact VersionId readback (`scripts/primary_statements/upload_artifacts_v1.py`).
Evidence code: commit `9b928a6032fc434072a9bfa833d50b73c41bbd9e`, pushed on
`codex/primary-statements-claude`.

Prefix: `bctc-ai/primary-statements/2025-current/v1/runs/`

## Artifact manifests (each lists every object key, VersionId, SHA-256, size)

| Manifest key (under prefix) | VersionId | SHA-256 | Objects |
| --- | --- | --- | --- |
| `full271-20261021T163936Z/run-files/ARTIFACT_MANIFEST.json` | `IYUAeXx69WlneNHn_Rcq7xE9c0xFoVSl` | `fd0e721d6d68fb0e3bb02bd55d56c73cb6f03244707ea8d7a4353bf037b9035f` | 274 (store, rebuild ids, run manifest, 271 workbooks) |
| `common204-20261021T164639Z/run-files/ARTIFACT_MANIFEST.json` | `OZzrtpZCEzQ5qmVOCJUhEjOxFOd_ZSWl` | `6cbd954f8aad1b96a46f08c5f9b660072aca25777c64ede74b27d1b1594970b8` | 207 (store, rebuild ids, run manifest, 204 workbooks) |
| `full271-20261021T163936Z/ARTIFACT_MANIFEST.json` | `UJqBqIyP4HOdjPWn3wWyjt8SNp1rf5Ud` | `d7d223fc36d0be7201d162a76ab4f50a69521db4a25fa02df5048009a804a7ad` | 7 receipts (`extra/`) |
| `common204-20261021T164639Z/ARTIFACT_MANIFEST.json` | `UBTthb_btwmEkJVF4ScEi3yzTW4C5UsT` | `ba5d6f970ac208eda59bd54ae0fa8b6175171dcfa4c7ab5e067f97e552f425f4` | 2 receipts (`extra/`) |

The two receipt-only manifests were the first upload attempt: the run folder
was read through a `\\wsl.localhost` path that yields no files on Windows, so
only `--extra` receipts were written. They are kept (immutable) and the run
files were uploaded from a byte-identical local staging copy under
`run-files/`. The uploader now refuses an empty run folder.

## Key objects

| Object (under prefix) | VersionId | SHA-256 | Bytes |
| --- | --- | --- | --- |
| `full271-20261021T163936Z/run-files/primary-results.sqlite3` | `KITfN3iOt7uaWdPmUoT8wwYxDBy85f19` | `4314ddc2fd33cc5d6b4530dfb6dc98cfe5946f39001038614748a8a4974ed95d` | 267,972,608 |
| `full271-20261021T163936Z/run-files/run-manifest.json` | `rscmQi2Gg4VkIjy5JWKI1J45SwljYlte` | `c37cc297014fa086745eb1dd670c4c93b0d92209f08c1877c0a2960672fa6307` | 148,598 |
| `full271-20261021T163936Z/run-files/rebuild-result-ids.json` | `STbbV.y0wA2uUcBS8CzH8SiaG.dxuJ7i` | `871979c75a56cbe053c3c2403740282b1270a7f6f099b603c0a88d620f56a280` | 24,553 |
| `common204-20261021T164639Z/run-files/primary-results.sqlite3` | `nxK7MiptTiBhomVld81vmesnwQi0tb0I` | `0f7e7c5541b5708dfcb8153a1aa9db8bf2e92d4c67285a0543f260f71ff41cb5` | 201,703,424 |
| `common204-20261021T164639Z/run-files/run-manifest.json` | `38cUgRbTPmTVczunX6_.288sSjsKyrAL` | `67423bc7cd01bf11eed41f3fdd872c18bc058abbf59d88631064585a2b9ae1d7` | 114,177 |
| `common204-20261021T164639Z/run-files/rebuild-result-ids.json` | `MHQ8ZdqsSEp8RwerQAXcFn7W80.lBRiC` | `d6d70726f42d2e08f2affaa2ede5f7f0f3a967031d85410ab30b2da4ea6ab005` | 18,456 |
| `full271-20261021T163936Z/extra/preflight-final.json` | `JXfXfvi3boa.BXqiGtJsxpAJtSLegIIg` | `368b2d7ec57bf6ffb0add8255b7c6588d965ff0ff3dbb96cef8126ac7c6c24f5` | 22,011 |
| `full271-20261021T163936Z/extra/pytest-9b928a6.xml` | `0zdrhZzg4coV1WdSOOdl6Y7G73HwxBFh` | `02d74c3e7d4baa8ec1d3d822ec0d1ba70aa2b7b660f27f526353d89c58fbf399` | 12,364 |
| `full271-20261021T163936Z/extra/pdf-audit-full271-20261021T163936Z.json` | `pCDn7lDOldUpT6zrHeF8eNY8_0DYYJ6A` | `7e5830bce9a0b6ddbb33b9ef37197689c0f9d22dd75fd4e9b8fd7fc99b82a7c9` | 7,079 |
| `full271-20261021T163936Z/extra/compare-full271-common204.json` | `h53SrDjYXPVa0P.mA_KD0fetH406.glP` | `a9050fd88205d84b95d7e8b81c49cb2f40ac7e557c5fee4510cc2fb9863c502a` | 4,478 |
| `full271-20261021T163936Z/extra/preflight-20261021T205345Z.json` | `GwRmpvWVZWlNA4zxHjk1yJb.VenPaa9Q` | `387c8ca147a31200a62ea9bcb7feabf0cf8aaea6cd0046cbfd4f937ef5b07f62` | 20,465 |
| `full271-20261021T163936Z/extra/preflight-9b928a6.json` | `DuU358bKHFs1bWAcIssEtD37TDOG5f6J` | `5822b9cc1392108b5cc2eb28c4091361d539fb2e990d42e9a36e5bd90fcc84b9` | 20,413 |

`preflight-9b928a6.json` records the pre-fix git gate (FAIL: it required
HEAD == base after commits); `preflight-final.json` is the corrected gate,
12/12 PASS at `d2c7d8f`.

Workbook keys: `<run>/run-files/workbooks/<NNN>_<plan>_PRIMARY_ONLY.xlsx`, each
listed with VersionId and SHA-256 in its run-files manifest; the same SHA-256
values appear in `run-manifest.json` with status `PASS_EXACT_READBACK`.
