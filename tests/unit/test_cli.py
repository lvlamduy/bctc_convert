from __future__ import annotations

from bctc_ai.cli.main import build_parser


def test_history_index_cli_uses_uri_environment_and_safe_defaults():
    arguments = build_parser().parse_args(["history-index"])

    assert arguments.mongo_uri_env == "BCTC_HISTORY_MONGO_URI"
    assert arguments.output == "data/local/historical_weak_reference.duckdb"
    assert arguments.registry == "data/registered/historical_weak_reference_registry.json"
    assert arguments.replace is False


def test_history_index_cli_fails_before_build_when_uri_environment_is_missing(monkeypatch, capsys):
    monkeypatch.delenv("BCTC_HISTORY_MONGO_URI", raising=False)
    arguments = build_parser().parse_args(["history-index"])

    assert arguments.handler(arguments) == 2
    assert "is not set" in capsys.readouterr().err


def test_review_audit_cli_has_rebuild_safe_defaults():
    arguments = build_parser().parse_args(["review-audit"])
    assert arguments.policy == "config/reference/human-review-v1.yaml"
    assert not arguments.allow_missing_sources


def test_s3_backup_offload_and_hydrate_cli_defaults_are_fail_safe():
    parser = build_parser()
    backup = parser.parse_args(["s3-backup", "--staging", "/tmp/staging"])
    assert backup.config == "config/backup/s3-v1.toml"
    assert backup.full_content_restore is None
    assert backup.workers is None

    offload = parser.parse_args(
        [
            "s3-offload",
            "--manifest",
            "/tmp/manifest.json",
            "--run-record",
            "/tmp/run.json",
            "--asset-class",
            "source_pdf",
        ]
    )
    assert not offload.apply

    hydrate = parser.parse_args(
        [
            "s3-hydrate",
            "--manifest-key",
            "bctc-ai/snapshots/id/manifest.json",
            "--manifest-sha256",
            "a" * 64,
            "--logical-path",
            "vietstock_bctc/AAA/report.pdf",
        ]
    )
    assert hydrate.logical_path == ["vietstock_bctc/AAA/report.pdf"]
    assert hydrate.asset_class == []
