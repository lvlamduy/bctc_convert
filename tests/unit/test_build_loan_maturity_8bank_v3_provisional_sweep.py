from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if "vietocr_semantic_page_binding_v3" not in sys.modules:
    _load(
        "vietocr_semantic_page_binding_v3",
        _ROOT / "scripts/experiments/vietocr_semantic_page_binding_v3.py",
    )
sweep_v1 = _load(
    "build_loan_maturity_8bank_v3_provisional_sweep",
    _ROOT / "scripts/experiments/build_loan_maturity_8bank_v3_provisional_sweep.py",
)


def _source() -> dict:
    return {
        "source_local_page_id": "ssv2:page:" + "1" * 64,
        "source_locator": {"physical_page": 42, "source_sha256": "2" * 64},
    }


def _binding() -> dict:
    return {"binding_id": "binding", "samples": []}


@pytest.mark.parametrize(
    "reasons",
    (
        [sweep_v1._NATIVE_REASON],
        sorted(sweep_v1._TERMINAL_REASONS),
    ),
)
def test_hydrated_observation_is_exact_unresolved(reasons: list[str]) -> None:
    observation = sweep_v1._unresolved_observation(_source(), _binding(), reasons)

    assert observation["status"] == "UNRESOLVED"
    assert observation["candidate_regions"] == []
    assert observation["unresolved_reasons"] == reasons
    assert not any(observation["readiness"].values())


def test_unresolved_reasons_fail_closed_when_not_canonical() -> None:
    with pytest.raises(sweep_v1.E0046ProvisionalSweepError):
        sweep_v1._unresolved_observation(
            _source(),
            _binding(),
            list(reversed(sorted(sweep_v1._TERMINAL_REASONS))),
        )


def test_live_replay_rejects_coordinated_rehash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = {"binding": {"text": "authentic"}, "sweep_id": "live"}
    monkeypatch.setattr(sweep_v1, "_validate_sweep_shape", copy.deepcopy)
    monkeypatch.setattr(sweep_v1, "_build_payload", lambda _root: copy.deepcopy(expected))

    assert sweep_v1.validate_loan_maturity_8bank_v3_provisional_sweep(expected, _ROOT) == expected
    forged = copy.deepcopy(expected)
    forged["binding"]["text"] = "forged"
    forged["sweep_id"] = "coordinated-rehash"
    with pytest.raises(
        sweep_v1.E0046ProvisionalSweepError,
        match="does not replay from live authorities",
    ):
        sweep_v1.validate_loan_maturity_8bank_v3_provisional_sweep(forged, _ROOT)


def test_metrics_never_promote_numeric_or_mapping_verification() -> None:
    modes = (
        [sweep_v1._ORDINARY_MODE] * 2
        + [sweep_v1._NATIVE_MODE]
        + [sweep_v1._ORDINARY_MODE]
        + [sweep_v1._TERMINAL_MODE]
        + [sweep_v1._ORDINARY_MODE] * 3
    )
    trials = [
        {
            "semantic_page_binding": {
                "binding_mode": mode,
                "metrics": {"all_ready_lines_bound_once": True},
            },
            "observation_candidate": {"status": "UNRESOLVED"},
            "semantic_graph": {"status": "UNRESOLVED"},
            "schema_candidate": {"status": "UNRESOLVED_GRAPH_NOT_ACCEPTED"},
        }
        for mode in modes
    ]

    metrics = sweep_v1._metrics(trials)
    assert metrics["ordinary_structural_evaluation_count"] == 6
    assert metrics["native_numeric_authority_blocked_count"] == 1
    assert metrics["terminal_source_blocked_count"] == 1
    assert metrics["independent_numeric_evaluated_count"] == 0
    assert metrics["independent_mapping_evaluated_count"] == 0
    assert metrics["verified_mapping_count"] == 0
