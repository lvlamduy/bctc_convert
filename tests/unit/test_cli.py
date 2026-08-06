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
