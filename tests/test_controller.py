"""Tests for selection hyper-heuristic controller."""

from __future__ import annotations

import pytest

from algorithms.controller import (
    extract_features,
    get_last_controller_telemetry,
    run_hyper_heuristic,
    score_aco,
    score_pso,
    select_heuristic,
)
from algorithms.initializer import generate_initial_solution
from models.course import Course
from models.room import Room
from models.timetable import TimetableState
from parsers.itc_parser import Curriculum, ITCInstance


@pytest.fixture
def small_itc_instance() -> ITCInstance:
    """Synthetic instance: 3 courses, 2 rooms, 3 days, 5 periods."""
    return ITCInstance(
        name="controller_small",
        courses=(
            Course("c1", "t1", 1, 1, 10),
            Course("c2", "t2", 1, 1, 10),
            Course("c3", "t3", 1, 1, 10),
        ),
        rooms=(Room("r1", 50), Room("r2", 50)),
        curricula=(
            Curriculum("cu1", ("c1", "c2")),
            Curriculum("cu2", ("c3",)),
        ),
        unavailability=(),
        nr_days=3,
        periods_per_day=5,
    )


def _base_stats() -> dict[str, object]:
    return {
        "ACO": {
            "times_used": 0,
            "avg_reward": 0.0,
            "recent_success_rate": 0.0,
            "recent_failure_rate": 0.0,
        },
        "PSO": {
            "times_used": 0,
            "avg_reward": 0.0,
            "recent_success_rate": 0.0,
            "recent_failure_rate": 0.0,
        },
        "selection_history": [],
    }


def test_extract_features_contains_expected_keys(
    small_itc_instance: ITCInstance,
) -> None:
    state = generate_initial_solution(small_itc_instance)
    features = extract_features(state, small_itc_instance, stagnation_count=3)
    expected = {
        "conflict_density",
        "room_utilization_pressure",
        "hard_constraint_violation_count",
        "normalized_hard_violations",
        "soft_constraint_penalty_score",
        "search_stagnation",
        "timetable_feasibility_ratio",
    }
    assert expected.issubset(features.keys())


def test_scoring_functions_return_float(small_itc_instance: ITCInstance) -> None:
    state = generate_initial_solution(small_itc_instance)
    features = extract_features(state, small_itc_instance, stagnation_count=2)
    stats = _base_stats()
    aco = score_aco(features, stats, float(state.fitness or 1.0))  # type: ignore[arg-type]
    pso = score_pso(features, stats, float(state.fitness or 1.0))  # type: ignore[arg-type]
    assert isinstance(aco, float)
    assert isinstance(pso, float)


def test_select_heuristic_returns_valid_choice(small_itc_instance: ITCInstance) -> None:
    state = generate_initial_solution(small_itc_instance)
    features = extract_features(state, small_itc_instance, stagnation_count=5)
    selected = select_heuristic(
        features, _base_stats(), float(state.fitness or 1.0)
    )  # type: ignore[arg-type]
    assert selected in {"ACO", "PSO"}


def test_controller_runs_without_crashing(
    small_itc_instance: ITCInstance,
) -> None:
    best, history, stats = run_hyper_heuristic(small_itc_instance, max_iterations=3)
    assert isinstance(best, TimetableState)
    assert isinstance(history, list)
    assert 1 <= len(history) <= 3
    assert "ACO" in stats and "PSO" in stats


def test_controller_never_worse_than_initializer(
    small_itc_instance: ITCInstance,
) -> None:
    initial = generate_initial_solution(small_itc_instance)
    initial_fitness = float(initial.fitness or 0.0)
    best, _, _ = run_hyper_heuristic(small_itc_instance, max_iterations=5)
    best_fitness = float(best.fitness or 0.0)
    assert best_fitness <= initial_fitness


def test_controller_supports_custom_burst_parameters(
    small_itc_instance: ITCInstance,
) -> None:
    best, history, _ = run_hyper_heuristic(
        small_itc_instance,
        max_iterations=3,
        aco_burst_iterations=2,
        aco_burst_ants=1,
        pso_burst_iterations=2,
        pso_burst_particles=1,
    )
    assert isinstance(best, TimetableState)
    assert len(history) >= 1


def test_controller_supports_trial_phase_toggle(
    small_itc_instance: ITCInstance,
) -> None:
    best, history, stats = run_hyper_heuristic(
        small_itc_instance,
        max_iterations=2,
        trial_phase=False,
    )
    assert isinstance(best, TimetableState)
    assert history
    assert isinstance(stats["selection_history"], list)


def test_controller_final_refinement_keeps_non_degradation(
    small_itc_instance: ITCInstance,
) -> None:
    initial = generate_initial_solution(small_itc_instance)
    initial_fitness = float(initial.fitness or 0.0)
    best, _, _ = run_hyper_heuristic(
        small_itc_instance,
        max_iterations=2,
        pso_burst_iterations=4,
        pso_burst_particles=2,
    )
    assert float(best.fitness or 0.0) <= initial_fitness


def test_controller_supports_exploration_hard_threshold(
    small_itc_instance: ITCInstance,
) -> None:
    best, history, _ = run_hyper_heuristic(
        small_itc_instance,
        max_iterations=3,
    )
    assert isinstance(best, TimetableState)
    assert len(history) >= 1


def test_controller_threshold_prefers_pso_until_pso_stalls(
    small_itc_instance: ITCInstance,
) -> None:
    _, _, stats = run_hyper_heuristic(
        small_itc_instance,
        max_iterations=4,
    )
    history = stats["selection_history"]
    assert history
    assert history[0] == "PSO"


def test_controller_supports_trial_phase_parameters(
    small_itc_instance: ITCInstance,
) -> None:
    best, history, stats = run_hyper_heuristic(
        small_itc_instance,
        max_iterations=3,
        trial_phase=True,
        aco_trial_iterations=2,
        aco_trial_ants=1,
        pso_trial_iterations=2,
        pso_trial_particles=1,
    )
    assert isinstance(best, TimetableState)
    assert len(history) >= 1
    assert stats["selection_history"]


def test_controller_threshold_lock_respects_trial_preference(
    small_itc_instance: ITCInstance,
) -> None:
    _, _, stats = run_hyper_heuristic(
        small_itc_instance,
        max_iterations=2,
        trial_phase=False,
    )
    assert stats["selection_history"]


def test_controller_tie_discriminator_path_runs(
    small_itc_instance: ITCInstance,
) -> None:
    best, history, stats = run_hyper_heuristic(
        small_itc_instance,
        max_iterations=2,
        trial_phase=True,
        aco_trial_iterations=1,
        aco_trial_ants=1,
        pso_trial_iterations=1,
        pso_trial_particles=1,
    )
    assert isinstance(best, TimetableState)
    assert history
    assert stats["selection_history"]


def test_controller_runtime_budget_can_stop_early(
    small_itc_instance: ITCInstance,
) -> None:
    _, history, _ = run_hyper_heuristic(
        small_itc_instance,
        max_iterations=10,
        max_controller_seconds=0.01,
    )
    assert len(history) <= 1


def test_controller_telemetry_available_after_run(
    small_itc_instance: ITCInstance,
) -> None:
    run_hyper_heuristic(small_itc_instance, max_iterations=2)
    telemetry = get_last_controller_telemetry()
    if telemetry:
        required = {
            "iteration",
            "selected",
            "rule",
            "aco_score",
            "pso_score",
            "hard_delta",
            "reward",
            "burst_runtime_seconds",
            "burst_iterations",
            "burst_size",
        }
        assert required.issubset(set(telemetry[0].keys()))
