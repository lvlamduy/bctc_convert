# VPS checkpoint — 2026-09-05

Trạng thái bảo toàn trước khi tắt/xoá VPS. Không có provider job nào đang chạy; không đọc hoặc ghi API key.

## Git

Remote: `https://github.com/lvlamduy/bctc_convert.git`

Các branch WIP/evidence đã push:

| Branch | HEAD | Trạng thái |
|---|---|---|
| `codex/vps-handoff-20260905` | `1a5077097d335816b5421ea5762702cce78a10a3` | tài liệu tiếp tục |
| `codex/f30-service-leaves-vps` | `6a620717e18dbf366d10ae7771be523a8fadb4fe` | WIP/HOLD |
| `codex/shared-source-ref-unique-vps` | `b6cfdc53a21b36bf03503d02e67f30e810152261` | WIP/HOLD, cần review độc lập |
| `codex/f18-row-level-strict-subset-vps` | `d063e8ffe6fe45b572ac4947f5342cb503c98728` | prototype chưa review |
| `codex/f36-operating-expense-vps` | `9a01a391dc097283ba436ef01e76ce56d42f4a5b` | terminal HOLD |
| `codex/f36-owner-axis-partition-speed` | `fc9b6218c0c23e6053a2c199c69ca5234d712af8` | speed WIP, chưa checkpoint cuối |
| `codex/f37-credit-risk-provision-vps` | `6feb29895c0bee541286b9059d63ebf488b07c60` | terminal HOLD |
| `codex/cross-family-audit-vps` | `3f4aa28f4b617a7adc2f6edb279a0b9c17309ccf` | audit |

Nhánh checkout chính lúc chốt là `codex/rebuild-bootstrap`, sạch, HEAD `e1d430a` và đã tồn tại trên `origin`.

## S3 evidence

Bucket `test-s3-duylv`, private, versioning Enabled, SSE-S3 (`AES256`). PDF/database archives authority đã có trong migration checkpoint; không upload lại.

- Handoff: `bctc-ai/coordination/2025-current/v1/handoffs/20260905-vps-handoff-fa36ff9/`
- F30 evidence/full271: `bctc-ai/coordination/2025-current/v1/artifacts/vps/20260905-f30-service-leaves-6a62071-wip-hold-v1/`
- F36 checkpoint: `.../20260905-f36-provenance-dedup-9a01a391-v1/`
- F37 evidence + additive self-containment: `.../20260905-f37-credit-risk-provision-6feb298-v1/`
- Cross-family audit: `.../20260905-cross-family-coverage-speed-audit-v1/`
- Shared provenance audit: `.../20260905-shared-source-ref-provenance-audit-v1/`
- Metadata/provenance proof and residual audits: `.../20260905-metadata-provenance-proof-v1/` (44 objects, 2,297,639 bytes)

F30 đã có `SHA256SUMS.txt` (19 file, checksum manifest SHA-256 `a879b9d190d80b420b40fb4b064badccd8f01c1991257f49a9f20d36dd46d9d3`), VersionId `DA.bmeyttvtR2.oMKXGUTGIe5zQ0aMxz`.

F37 có 51 object versions sau khi bổ sung bốn file self-containment và hai manifest correction/additive; vẫn giữ trạng thái pending independent re-audit, không giả mạo terminal checkpoint.

## Trạng thái công việc

- Phạm vi: báo cáo năm 2025 đến hiện tại; Gemini JSON → database là pipeline authority.
- F30: 202 READY / 68 NOT_OBSERVED / 1 U trên Full271; tests 137/137 PASS; còn lỗi shared source-reference uniqueness nên HOLD.
- Shared provenance bounded replay: 24 docs / 188 mappings / 87 redundant refs → 0, semantic axes không đổi; cần independent review.
- F36/F37: artifact, database/evidence và checkpoint đã bảo toàn; đều terminal HOLD theo gate.
- F18: prototype row-level strict-subset đã push, chưa được review/merge.

## Khôi phục trên máy mới

```bash
git clone https://github.com/lvlamduy/bctc_convert.git
cd bctc_convert
git fetch --all --prune
git switch codex/vps-handoff-20260905
less docs/operations/VPS_HANDOFF_2026-09-05.md
less docs/operations/VPS_RESUME_PROMPT.md
```

Giữ `codex-session.passphrase` ở ngoài Git/S3 và dùng đúng migration manifest/version IDs. Không xoá hoặc overwrite object S3; tải theo VersionId, kiểm SHA trước giải nén. Tiếp tục theo thứ tự handoff, bắt đầu bằng restore/validate rồi mới xử lý family tiếp theo.
