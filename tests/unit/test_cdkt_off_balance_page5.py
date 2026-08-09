from __future__ import annotations

import shutil
from pathlib import Path

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.tables.cdkt_off_balance_page5 import (
    CDKT_OFF_BALANCE_PAGE5_POLICY_RELATIVE_PATH,
    load_cdkt_off_balance_page5_policy,
    parse_cdkt_off_balance_page5,
)

_EVIDENCE_PATHS = (
    Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf"),
    Path(
        "output/calibration/recovery-e0027-mbb-q1-2026-role-c-20260807/"
        "ppocrv6-page-0005/ocr_result.json"
    ),
    Path(
        "output/calibration/recovery-e0027-mbb-q1-2026-20260807/"
        "eebeda2ebc09b0d42032/renders/page-0005.png"
    ),
)


def _parse(project_root: Path):
    policy = load_cdkt_off_balance_page5_policy(
        project_root / CDKT_OFF_BALANCE_PAGE5_POLICY_RELATIVE_PATH,
        project_root,
    )
    return parse_cdkt_off_balance_page5(policy)


def test_page5_reconstructs_exact_source_rows_cells_and_accounting(project_root: Path) -> None:
    result = _parse(project_root)

    assert result.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert result.source_ocr_sha256 == (
        "27e5cc72f71a4b759bd0a72e28a9178aa55faaf04aa2cd67812322d83b591d68"
    )
    assert result.source_render_sha256 == (
        "7f2574bf11ad7df3d93dc6256c8aa631f6851f8e0056e7bed3c0195d8eeccc6a"
    )
    assert (result.source_row_count, result.physical_cell_count) == (11, 22)
    assert (result.value_cell_count, result.blank_cell_count) == (18, 4)
    assert [row.report_norm_id for row in result.rows] == list(range(6038, 6049))
    assert all(
        row.label_bbox.x1 <= result.render_width
        and row.label_bbox.y1 <= result.render_height
        and row.label_similarity >= 0.72
        for row in result.rows
    )
    by_id = {row.report_norm_id: row for row in result.rows}
    assert all(
        cell.observation is ObservationKind.BLANK
        for report_norm_id in (6038, 6039)
        for cell in by_id[report_norm_id].cells
    )
    assert {
        report_norm_id: tuple(cell.displayed_value for cell in by_id[report_norm_id].cells)
        for report_norm_id in range(6040, 6049)
    } == {
        6040: (1_681_823, 1_684_717),
        6041: (723_980_330, 618_888_427),
        6042: (1_302_737, 9_738_358),
        6043: (2_160_046, 8_752_345),
        6044: (359_933_489, 299_830_234),
        6045: (360_584_058, 300_567_490),
        6046: (71_763_365, 59_728_018),
        6047: (186_067_393, 190_317_517),
        6048: (117_681_586, 127_878_633),
    }
    assert by_id[6044].visible_label == "Cam kết mua giao dịch hoán đổi ngoại tệ"
    assert by_id[6045].visible_label == "Cam kết bán giao dịch hoán đổi ngoại tệ"
    assert result.accounting_checks_passed == (
        "6041=SUM(6042,6043,6044,6045)/CURRENT",
        "6041=SUM(6042,6043,6044,6045)/COMPARATIVE",
    )


def test_page5_ocr_render_binding_is_portable_across_project_roots(
    project_root: Path, tmp_path: Path
) -> None:
    relocated = tmp_path / "relocated-project"
    for relative in (CDKT_OFF_BALANCE_PAGE5_POLICY_RELATIVE_PATH, *_EVIDENCE_PATHS):
        target = relocated / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project_root / relative, target)

    result = _parse(relocated)

    assert result.source_render_path == _EVIDENCE_PATHS[2].as_posix()
    assert result.source_row_count == 11
    assert result.value_cell_count == 18
