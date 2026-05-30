"""Selection hyper-heuristic controller for ACO/PSO orchestration."""

from __future__ import annotations

import time
from typing import TypedDict

from algorithms.aco import initialize_aco_state, run_aco, run_aco_with_state
from algorithms.fitness import evaluate_timetable
from algorithms.initializer import generate_initial_solution
from algorithms.pso import initialize_pso_state, run_pso, run_pso_with_state
from algorithms.repair import get_conflicting_lectures
from models.timetable import TimetableState
from parsers.itc_parser import ITCInstance

HISTORICAL_WEIGHT = 0.001
HARD_DELTA_SCORE_WEIGHT = 0.05
TRIAL_BIAS_ITERATIONS = 3
TRIAL_BIAS_BONUS = 0.12
TRIAL_SCORE_MARGIN = 0.03
TRIAL_MIN_REMAINING_SECONDS = 20.0
BURST_MIN_REMAINING_SECONDS = 12.0
BURST_SHRINK_HEADROOM = 1.25
_DEFAULT_SCORE_WEIGHTS: dict[str, dict[str, float]] = {
    "ACO": {
        "conflict_density": 0.4,
        "normalized_hard_violations": 0.3,
        "infeasibility": 0.3,
    },
    "PSO": {
        "search_stagnation": 0.5,
        "feasibility_ratio": 0.3,
        "low_conflict_density": 0.2,
    },
}
_SCORE_WEIGHTS: dict[str, dict[str, float]] = {
    "ACO": dict(_DEFAULT_SCORE_WEIGHTS["ACO"]),
    "PSO": dict(_DEFAULT_SCORE_WEIGHTS["PSO"]),
}

_LAST_CONTROLLER_TELEMETRY: list[dict[str, float | int | str]] = []


class HeuristicStats(TypedDict):
    times_used: int
    avg_reward: float
    recent_success_rate: float
    recent_failure_rate: float


class ControllerStats(TypedDict):
    ACO: HeuristicStats
    PSO: HeuristicStats
    selection_history: list[str]


def get_last_controller_telemetry() -> list[dict[str, float | int | str]]:
    """Return per-iteration telemetry from the latest controller run."""
    return [dict(item) for item in _LAST_CONTROLLER_TELEMETRY]


def set_controller_score_weights(
    *,
    aco_conflict_density: float,
    aco_normalized_hard_violations: float,
    aco_infeasibility: float,
    pso_search_stagnation: float,
    pso_feasibility_ratio: float,
    pso_low_conflict_density: float,
) -> None:
    """Override controller score weights for sensitivity experiments."""
    _SCORE_WEIGHTS["ACO"] = {
        "conflict_density": float(aco_conflict_density),
        "normalized_hard_violations": float(aco_normalized_hard_violations),
        "infeasibility": float(aco_infeasibility),
    }
    _SCORE_WEIGHTS["PSO"] = {
        "search_stagnation": float(pso_search_stagnation),
        "feasibility_ratio": float(pso_feasibility_ratio),
        "low_conflict_density": float(pso_low_conflict_density),
    }


def reset_controller_score_weights() -> None:
    """Restore default controller score weights."""
    _SCORE_WEIGHTS["ACO"] = dict(_DEFAULT_SCORE_WEIGHTS["ACO"])
    _SCORE_WEIGHTS["PSO"] = dict(_DEFAULT_SCORE_WEIGHTS["PSO"])


def get_controller_score_weights() -> dict[str, dict[str, float]]:
    """Return a copy of currently active controller score weights."""
    return {
        "ACO": dict(_SCORE_WEIGHTS["ACO"]),
        "PSO": dict(_SCORE_WEIGHTS["PSO"]),
    }


def extract_features(
    state: TimetableState,
    instance: ITCInstance,
    stagnation_count: int,
) -> dict[str, float | int]:
    """Extract state and search-process features for hyper-heuristic selection."""
    evaluate_timetable(state, instance)

    total_assignments = max(1, len(state.assignments))
    hard = int(state.hard_violations or 0)
    soft = float(state.soft_penalty or 0.0)
    conflicts = get_conflicting_lectures(state, instance)

    avg_students = (
        sum(c.students for c in instance.courses) / len(instance.courses)
        if instance.courses
        else 0.0
    )
    avg_room_capacity = (
        sum(r.capacity for r in instance.rooms) / len(instance.rooms)
        if instance.rooms
        else 0.0
    )
    room_utilization_pressure = (
        avg_students / avg_room_capacity if avg_room_capacity > 0 else 0.0
    )

    valid_assignments = 0
    room_ids = {r.room_id for r in instance.rooms}
    for idx, assignment in enumerate(state.assignments):
        placed = (
            assignment.room_id is not None
            and assignment.day is not None
            and assignment.period is not None
            and assignment.room_id in room_ids
            and 0 <= assignment.day < instance.nr_days
            and 0 <= assignment.period < instance.periods_per_day
        )
        if placed and idx not in conflicts:
            valid_assignments += 1

    conflict_density = hard / total_assignments
    normalized_hard_violations = hard / total_assignments
    feasibility_ratio = valid_assignments / total_assignments
    search_stagnation = min(1.0, stagnation_count / 10.0)

    return {
        "conflict_density": conflict_density,
        "room_utilization_pressure": room_utilization_pressure,
        "hard_constraint_violation_count": hard,
        "normalized_hard_violations": normalized_hard_violations,
        "soft_constraint_penalty_score": soft,
        "search_stagnation": search_stagnation,
        "timetable_feasibility_ratio": feasibility_ratio,
    }


def score_aco(
    features: dict[str, float | int],
    heuristic_stats: ControllerStats,
    previous_fitness: float,
) -> float:
    """Compute adjusted suitability score for ACO."""
    weights = _SCORE_WEIGHTS["ACO"]
    base_score = (
        weights["conflict_density"] * float(features["conflict_density"])
        + weights["normalized_hard_violations"]
        * float(features["normalized_hard_violations"])
        + weights["infeasibility"] * (1.0 - float(features["timetable_feasibility_ratio"]))
    )
    avg_reward = float(heuristic_stats["ACO"]["avg_reward"])
    normalized_reward = avg_reward / (abs(previous_fitness) + 1.0)
    failure_penalty = float(heuristic_stats["ACO"]["recent_failure_rate"]) * 0.5
    return base_score + HISTORICAL_WEIGHT * normalized_reward - failure_penalty


def score_pso(
    features: dict[str, float | int],
    heuristic_stats: ControllerStats,
    previous_fitness: float,
) -> float:
    """Compute adjusted suitability score for PSO."""
    weights = _SCORE_WEIGHTS["PSO"]
    base_score = (
        weights["search_stagnation"] * float(features["search_stagnation"])
        + weights["feasibility_ratio"] * float(features["timetable_feasibility_ratio"])
        + weights["low_conflict_density"] * (1.0 - float(features["conflict_density"]))
    )
    avg_reward = float(heuristic_stats["PSO"]["avg_reward"])
    normalized_reward = avg_reward / (abs(previous_fitness) + 1.0)
    failure_penalty = float(heuristic_stats["PSO"]["recent_failure_rate"]) * 0.5
    return base_score + HISTORICAL_WEIGHT * normalized_reward - failure_penalty


def select_heuristic(
    features: dict[str, float | int],
    heuristic_stats: ControllerStats,
    previous_fitness: float,
) -> str:
    """Pick exactly one heuristic for this iteration."""
    aco_score = score_aco(features, heuristic_stats, previous_fitness)
    pso_score = score_pso(features, heuristic_stats, previous_fitness)
    return "ACO" if aco_score >= pso_score else "PSO"


def run_hyper_heuristic(
    instance: ITCInstance,
    max_iterations: int = 10,
    aco_burst_iterations: int = 15,
    aco_burst_ants: int = 5,
    pso_burst_iterations: int = 15,
    pso_burst_particles: int = 5,
    trial_phase: bool = True,
    aco_trial_iterations: int = 5,
    aco_trial_ants: int = 3,
    pso_trial_iterations: int = 5,
    pso_trial_particles: int = 3,
    max_controller_seconds: float | None = None,
) -> tuple[TimetableState, list[float], ControllerStats]:
    """Run a selection hyper-heuristic over short ACO/PSO bursts."""
    initial_state = generate_initial_solution(instance)
    evaluate_timetable(initial_state, instance)
    initial_fitness = float(initial_state.fitness or float("inf"))

    best_state = initial_state.copy()
    evaluate_timetable(best_state, instance)
    best_fitness = float(best_state.fitness or float("inf"))
    aco_state = initialize_aco_state(instance, starting_state=best_state)
    pso_state = initialize_pso_state(
        instance,
        num_particles=pso_burst_particles,
        starting_state=best_state,
    )
    history: list[float] = []
    stagnation_count = 0
    no_improve_iterations = 0
    heuristic_stats: ControllerStats = {
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
    preferred_heuristic = "PSO"
    smoothed_hard_gain: dict[str, float] = {"ACO": 0.0, "PSO": 0.0}
    improvement_streak: dict[str, int] = {"ACO": 0, "PSO": 0}
    controller_started = time.perf_counter()
    runtime_budget_seconds = (
        float(max_controller_seconds)
        if max_controller_seconds is not None
        else max(60.0, 15.0 * float(max_iterations))
    )
    telemetry: list[dict[str, float | int | str]] = []

    current_aco_iters = max(1, aco_burst_iterations)
    current_aco_ants = max(1, aco_burst_ants)
    current_pso_iters = max(1, pso_burst_iterations)
    current_pso_particles = max(1, pso_burst_particles)

    min_aco_iters = max(2, aco_burst_iterations // 3)
    min_aco_ants = max(1, aco_burst_ants // 2)
    min_pso_iters = max(2, pso_burst_iterations // 3)
    min_pso_particles = max(1, pso_burst_particles // 2)

    max_aco_iters = max(aco_burst_iterations, int(aco_burst_iterations * 1.3 + 0.5))
    max_aco_ants = max(aco_burst_ants, int(aco_burst_ants * 1.3 + 0.5))
    max_pso_iters = max(pso_burst_iterations, int(pso_burst_iterations * 1.3 + 0.5))
    max_pso_particles = max(
        pso_burst_particles, int(pso_burst_particles * 1.3 + 0.5)
    )
    avg_burst_seconds: dict[str, float] = {"ACO": 20.0, "PSO": 20.0}

    def _remaining_seconds() -> float:
        return max(0.0, runtime_budget_seconds - (time.perf_counter() - controller_started))

    if trial_phase and _remaining_seconds() >= TRIAL_MIN_REMAINING_SECONDS:
        trial_scale = 1.0
        if _remaining_seconds() < 2.0 * TRIAL_MIN_REMAINING_SECONDS:
            trial_scale = max(0.4, _remaining_seconds() / (2.0 * TRIAL_MIN_REMAINING_SECONDS))

        aco_trial_iters = max(1, int(aco_trial_iterations * trial_scale))
        aco_trial_ants_eff = max(1, int(aco_trial_ants * trial_scale))
        pso_trial_iters_eff = max(1, int(pso_trial_iterations * trial_scale))
        pso_trial_particles_eff = max(1, int(pso_trial_particles * trial_scale))

        aco_trial_start = time.perf_counter()
        aco_state, aco_trial_state, _ = run_aco_with_state(
            instance,
            aco_state,
            iterations=aco_trial_iters,
            num_ants=aco_trial_ants_eff,
            alpha=1.0,
            beta=2.0,
            evaporation_rate=0.1,
            verbose=False,
            early_stop_patience=2,
        )
        avg_burst_seconds["ACO"] = max(1e-6, time.perf_counter() - aco_trial_start)
        evaluate_timetable(aco_trial_state, instance)
        if _remaining_seconds() < TRIAL_MIN_REMAINING_SECONDS * 0.5:
            pso_trial_state = best_state.copy()
            evaluate_timetable(pso_trial_state, instance)
        else:
            pso_trial_start = time.perf_counter()
            pso_state, pso_trial_state, _ = run_pso_with_state(
                instance,
                pso_state,
                iterations=pso_trial_iters_eff,
                num_particles=pso_trial_particles_eff,
                w=0.4,
                c1=2.0,
                c2=0.3,
                verbose=False,
                early_stop_patience=2,
            )
            avg_burst_seconds["PSO"] = max(1e-6, time.perf_counter() - pso_trial_start)
            evaluate_timetable(pso_trial_state, instance)

        aco_trial_fit = float(aco_trial_state.fitness or float("inf"))
        pso_trial_fit = float(pso_trial_state.fitness or float("inf"))
        aco_trial_hard = int(aco_trial_state.hard_violations or 0)
        pso_trial_hard = int(pso_trial_state.hard_violations or 0)
        if (aco_trial_hard, aco_trial_fit) < (pso_trial_hard, pso_trial_fit):
            preferred_heuristic = "ACO"
        else:
            preferred_heuristic = "PSO"

        print(
            f"ACO trial result: fitness={aco_trial_fit:.2f}, hard={aco_trial_hard}, soft={aco_trial_state.soft_penalty}"
        )
        print(
            f"PSO trial result: fitness={pso_trial_fit:.2f}, hard={pso_trial_hard}, soft={pso_trial_state.soft_penalty}"
        )
        print(f"Initial preferred heuristic: {preferred_heuristic}")

    for iteration in range(1, max_iterations + 1):
        if time.perf_counter() - controller_started >= runtime_budget_seconds:
            print(
                f"Runtime budget reached ({runtime_budget_seconds:.1f}s); "
                f"stopping at iteration {iteration - 1}."
            )
            break

        features = extract_features(best_state, instance, stagnation_count)
        aco_score = score_aco(features, heuristic_stats, best_fitness)
        pso_score = score_pso(features, heuristic_stats, best_fitness)
        aco_score += HARD_DELTA_SCORE_WEIGHT * smoothed_hard_gain["ACO"]
        pso_score += HARD_DELTA_SCORE_WEIGHT * smoothed_hard_gain["PSO"]
        if trial_phase and iteration <= TRIAL_BIAS_ITERATIONS:
            if preferred_heuristic == "ACO":
                aco_score += TRIAL_BIAS_BONUS
            else:
                pso_score += TRIAL_BIAS_BONUS

        score_gap = abs(aco_score - pso_score)
        switched_by_rule = ""
        if trial_phase and (
            iteration <= TRIAL_BIAS_ITERATIONS or score_gap <= TRIAL_SCORE_MARGIN
        ):
            if preferred_heuristic == "ACO" and aco_score + TRIAL_SCORE_MARGIN >= pso_score:
                selected = "ACO"
                switched_by_rule = "trial_bias"
            elif preferred_heuristic == "PSO" and pso_score + TRIAL_SCORE_MARGIN >= aco_score:
                selected = "PSO"
                switched_by_rule = "trial_bias"
            elif aco_score == pso_score:
                selected = preferred_heuristic
                switched_by_rule = "trial_tie"
            else:
                selected = "ACO" if aco_score > pso_score else "PSO"
        elif aco_score == pso_score:
            selected = preferred_heuristic
            switched_by_rule = "score_tie"
        else:
            selected = "ACO" if aco_score > pso_score else "PSO"

        remaining = _remaining_seconds()
        if remaining < BURST_MIN_REMAINING_SECONDS:
            print(
                f"Remaining controller budget too low ({remaining:.1f}s); "
                f"stopping at iteration {iteration - 1}."
            )
            break

        if selected == "ACO":
            burst_iters = current_aco_iters
            burst_size = current_aco_ants
        else:
            burst_iters = current_pso_iters
            burst_size = current_pso_particles

        expected_burst = max(1.0, avg_burst_seconds[selected])
        if remaining < expected_burst * BURST_SHRINK_HEADROOM:
            scale = max(0.25, remaining / (expected_burst * BURST_SHRINK_HEADROOM))
            burst_iters = max(1, int(burst_iters * scale))
            burst_size = max(1, int(burst_size * scale))
            switched_by_rule = (
                f"{switched_by_rule}+budget_shrink" if switched_by_rule else "budget_shrink"
            )
        if remaining < expected_burst * 0.35:
            print(
                f"Skipping burst due low remaining budget ({remaining:.1f}s) vs expected "
                f"{expected_burst:.1f}s."
            )
            break
        if no_improve_iterations >= 3 and len(heuristic_stats["selection_history"]) >= 3:
            last_three = heuristic_stats["selection_history"][-3:]
            if len(set(last_three)) == 1:
                selected = _other_heuristic(last_three[-1])
                switched_by_rule = "stagnation_escape"

        fitness_before = best_fitness
        hard_before = int(best_state.hard_violations or 0)
        burst_started = time.perf_counter()
        prior_avg_burst = avg_burst_seconds[selected]
        if selected == "ACO":
            aco_state, candidate, _ = run_aco_with_state(
                instance,
                aco_state,
                iterations=burst_iters,
                num_ants=burst_size,
                alpha=1.0,
                beta=2.0,
                evaporation_rate=0.1,
                verbose=False,
                early_stop_patience=2,
            )
        else:
            pso_state, candidate, _ = run_pso_with_state(
                instance,
                pso_state,
                iterations=burst_iters,
                num_particles=burst_size,
                w=0.4,
                c1=2.0,
                c2=0.3,
                verbose=False,
                early_stop_patience=2,
            )
        burst_seconds = max(1e-6, time.perf_counter() - burst_started)
        avg_burst_seconds[selected] = 0.75 * avg_burst_seconds[selected] + 0.25 * burst_seconds
        evaluate_timetable(candidate, instance)

        fitness_after = float(candidate.fitness or float("inf"))
        hard_after = int(candidate.hard_violations or 0)
        hard_gain = hard_before - hard_after
        fitness_gain = fitness_before - fitness_after
        quality_reward = 10.0 * float(hard_gain) + (
            fitness_gain / max(abs(fitness_before), 1.0)
        )
        efficiency_reward = quality_reward / burst_seconds
        reward = 0.7 * quality_reward + 0.3 * efficiency_reward
        _update_heuristic_stats(heuristic_stats, selected, reward)

        best_hard = int(best_state.hard_violations or 0)
        improved_best = False
        if hard_after < best_hard and fitness_after <= initial_fitness:
            improved_best = True
        elif hard_after == best_hard and fitness_after < best_fitness:
            improved_best = True

        if improved_best:
            best_state = candidate
            best_fitness = fitness_after
            stagnation_count = 0
            no_improve_iterations = 0
            improvement_streak[selected] += 1
        else:
            stagnation_count += 1
            no_improve_iterations += 1
            improvement_streak[selected] = 0

        smoothed_hard_gain[selected] = (
            0.7 * smoothed_hard_gain[selected] + 0.3 * float(hard_gain)
        )
        other = _other_heuristic(selected)
        smoothed_hard_gain[other] *= 0.95

        runtime_ok = burst_seconds <= max(1.0, prior_avg_burst * 1.15)
        hard_improved = hard_gain > 0
        if selected == "ACO":
            if (
                improved_best
                and hard_improved
                and runtime_ok
                and improvement_streak[selected] >= 2
            ):
                current_aco_iters = min(max_aco_iters, current_aco_iters + 1)
                current_aco_ants = min(max_aco_ants, current_aco_ants + 1)
            else:
                current_aco_iters = max(min_aco_iters, current_aco_iters - 1)
                current_aco_ants = max(min_aco_ants, current_aco_ants - 1)
        else:
            if (
                improved_best
                and hard_improved
                and runtime_ok
                and improvement_streak[selected] >= 2
            ):
                current_pso_iters = min(max_pso_iters, current_pso_iters + 1)
                current_pso_particles = min(
                    max_pso_particles, current_pso_particles + 1
                )
            else:
                current_pso_iters = max(min_pso_iters, current_pso_iters - 1)
                current_pso_particles = max(
                    min_pso_particles, current_pso_particles - 1
                )

        heuristic_stats["selection_history"].append(selected)
        history.append(best_fitness)
        telemetry.append(
            {
                "iteration": iteration,
                "selected": selected,
                "rule": switched_by_rule or "score",
                "aco_score": round(aco_score, 6),
                "pso_score": round(pso_score, 6),
                "hard_delta": int(hard_gain),
                "reward": round(float(reward), 6),
                "burst_runtime_seconds": round(float(burst_seconds), 6),
                "burst_iterations": int(burst_iters),
                "burst_size": int(burst_size),
            }
        )
        print(
            f"Iteration {iteration}/{max_iterations} | "
            f"selected={selected} ({switched_by_rule or 'score'}) | "
            f"ACO={aco_score:.3f} PSO={pso_score:.3f} | "
            f"fitness={best_fitness:.2f} | hard={best_state.hard_violations}"
        )

        if int(best_state.hard_violations or 0) == 0:
            break
        if no_improve_iterations >= max(3, max_iterations // 2):
            break

    if (
        float(heuristic_stats["PSO"]["avg_reward"])
        > float(heuristic_stats["ACO"]["avg_reward"])
        and time.perf_counter() - controller_started < runtime_budget_seconds
    ):
        remaining = _remaining_seconds()
        if remaining >= BURST_MIN_REMAINING_SECONDS:
            refine_iters = min(max(1, pso_burst_iterations // 2), max(1, int(remaining / 12)))
            refine_particles = min(pso_burst_particles, max(1, int(remaining / 20)))
            refine_state, refine_history = run_pso(
                instance,
                iterations=refine_iters,
                num_particles=refine_particles,
                verbose=False,
                starting_state=best_state,
                early_stop_patience=2,
            )
            evaluate_timetable(refine_state, instance)
            refine_fitness = float(refine_state.fitness or float("inf"))
            if refine_fitness < best_fitness:
                best_state = refine_state
                best_fitness = refine_fitness
                history.extend(float(x) for x in refine_history)

    global _LAST_CONTROLLER_TELEMETRY
    _LAST_CONTROLLER_TELEMETRY = telemetry
    if best_fitness > initial_fitness:
        return initial_state, history, heuristic_stats
    print(
        f"Final best result: fitness={best_fitness:.2f}, "
        f"hard={best_state.hard_violations}, soft={best_state.soft_penalty}"
    )
    return best_state, history, heuristic_stats


def _update_heuristic_stats(
    heuristic_stats: ControllerStats,
    heuristic_name: str,
    reward: float,
) -> None:
    rec = heuristic_stats[heuristic_name]  # type: ignore[literal-required]
    prev_times = int(rec["times_used"])
    new_times = prev_times + 1
    prev_avg_reward = float(rec["avg_reward"])
    prev_success = float(rec["recent_success_rate"])
    success = 1.0 if reward > 0.0 else 0.0

    rec["times_used"] = new_times
    rec["avg_reward"] = (prev_avg_reward * prev_times + reward) / new_times
    rec["recent_success_rate"] = (prev_success * prev_times + success) / new_times
    rec["recent_failure_rate"] = 1.0 - float(rec["recent_success_rate"])


def _other_heuristic(name: str) -> str:
    return "ACO" if name == "PSO" else "PSO"
