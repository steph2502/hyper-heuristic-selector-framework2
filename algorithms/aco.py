"""Ant Colony Optimization for ITC timetabling."""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import TypeAlias

from algorithms.fitness import evaluate_timetable
from algorithms.initializer import generate_initial_solution
from algorithms.neighborhood import random_neighbor
from algorithms.repair import (
    feasible_slots_by_course,
    get_conflicting_lectures,
    repair_conflicts,
    ruin_and_recreate,
)
from models.timetable import LectureAssignment
from models.timetable import TimetableState
from parsers.itc_parser import ITCInstance

PheromoneKey: TypeAlias = tuple[int, str, int, int]

PHEROMONE_BASELINE = 1.0
PHEROMONE_MIN = 0.01
PHEROMONE_MAX = 10.0
DEPOSIT_Q = 1.0
MOVE_SAMPLES = 0
SWAP_SAMPLES = 0
ANT_START_DIVERSITY_STEPS = 1
STAGNATION_EXTRA_DIVERSITY_STEPS = 3
STAGNATION_EXTRA_DIVERSITY_TRIGGER = 10
STAGNATION_PHEROMONE_RESET_TRIGGER = 20
REPAIR_ATTEMPTS_PER_ANT = 5
MAX_FEASIBLE_SAMPLES = 2
MAX_FEASIBLE_SAMPLES_CONFLICT = 20
RUIN_STAGNATION_TRIGGER = 5
RUIN_LECTURES = 8
RUIN_ATTEMPTS = 3


@dataclass
class ACOState:
    """Persistent ACO state used by stateful controller bursts."""

    pheromone: dict[PheromoneKey, float]
    best_solution: TimetableState
    best_fitness: float
    stagnation_counter: int = 0
    iteration_count: int = 0
    no_improve_iters: int = 0
    base_state: TimetableState | None = None


def _init_pheromone(instance: ITCInstance, n_lectures: int) -> dict[PheromoneKey, float]:
    """Map (lecture_index, room_id, day, period) -> baseline pheromone."""
    pheromone: dict[PheromoneKey, float] = {}
    for lecture_index in range(n_lectures):
        for room in instance.rooms:
            for day in range(instance.nr_days):
                for period in range(instance.periods_per_day):
                    pheromone[(lecture_index, room.room_id, day, period)] = PHEROMONE_BASELINE
    return pheromone


def _pheromone_key(lecture_index: int, state: TimetableState) -> PheromoneKey | None:
    assignment = state.assignments[lecture_index]
    if assignment.room_id is None or assignment.day is None or assignment.period is None:
        return None
    return (lecture_index, assignment.room_id, assignment.day, assignment.period)


def _heuristic(
    current_hard: int,
    current_soft: float,
    candidate_hard: int,
    candidate_soft: float,
) -> float:
    """Desirability of a move: higher when hard/soft costs improve."""
    cur_f = current_hard * 1000.0 + current_soft
    cand_f = candidate_hard * 1000.0 + candidate_soft
    fitness_delta = cand_f - cur_f
    hard_delta = candidate_hard - current_hard

    cost_increase = max(0.0, fitness_delta) + max(0, hard_delta) * 1000.0
    return 1.0 / (1.0 + cost_increase)


def _priority_lecture_indices(state: TimetableState, instance: ITCInstance) -> list[int]:
    """Prioritize highest-conflict lectures, then remaining indices."""
    conflicts = list(get_conflicting_lectures(state, instance))
    if conflicts:
        assignment_to_indices: dict[tuple[str | None, int | None, int | None], list[int]] = defaultdict(list)
        for idx in conflicts:
            a = state.assignments[idx]
            assignment_to_indices[(a.room_id, a.day, a.period)].append(idx)

        scored = sorted(
            conflicts,
            key=lambda idx: (
                -len(
                    assignment_to_indices[
                        (
                            state.assignments[idx].room_id,
                            state.assignments[idx].day,
                            state.assignments[idx].period,
                        )
                    ]
                ),
                idx,
            ),
        )
        seen = set(scored)
        others = [i for i in range(len(state.assignments)) if i not in seen]
        random.shuffle(others)
        return scored + others
    indices = list(range(len(state.assignments)))
    random.shuffle(indices)
    return indices


def _candidates_for_lecture(
    state: TimetableState,
    instance: ITCInstance,
    lecture_index: int,
    slots_by_course: dict[str, tuple[tuple[str, int, int], ...]],
    *,
    prioritize_conflict: bool,
) -> list[tuple[TimetableState, int, float]]:
    candidates: list[tuple[TimetableState, int, float]] = []
    n = len(state.assignments)
    assignments = state.assignments
    current = assignments[lecture_index]

    feasible = list(slots_by_course.get(current.course_id, ()))
    random.shuffle(feasible)
    sample_cap = MAX_FEASIBLE_SAMPLES_CONFLICT if prioritize_conflict else MAX_FEASIBLE_SAMPLES
    samples = feasible[:sample_cap]
    for room_id, day, period in samples:
        new_assignments = list(assignments)
        new_assignments[lecture_index] = LectureAssignment(
            current.course_id, room_id, day, period
        )
        candidate = TimetableState(assignments=new_assignments)
        evaluate_timetable(candidate, instance)
        candidates.append(
            (
                candidate,
                int(candidate.hard_violations or 0),
                float(candidate.soft_penalty or 0.0),
            )
        )

    if n >= 2:
        others = [j for j in range(n) if j != lecture_index]
        for j in random.sample(others, min(SWAP_SAMPLES, len(others))):
            new_assignments = list(assignments)
            a = new_assignments[lecture_index]
            b = new_assignments[j]
            new_assignments[lecture_index] = LectureAssignment(
                a.course_id, b.room_id, b.day, b.period
            )
            new_assignments[j] = LectureAssignment(
                b.course_id, a.room_id, a.day, a.period
            )
            candidate = TimetableState(assignments=new_assignments)
            evaluate_timetable(candidate, instance)
            candidates.append(
                (
                    candidate,
                    int(candidate.hard_violations or 0),
                    float(candidate.soft_penalty or 0.0),
                )
            )

    if n < 2 or random.random() < 0.5:
        li = random.randrange(n)
        new_assignments = list(assignments)
        cur = new_assignments[li]
        feasible_li = list(slots_by_course.get(cur.course_id, ()))
        if feasible_li:
            room_id, day, period = random.choice(feasible_li)
            new_assignments[li] = LectureAssignment(cur.course_id, room_id, day, period)
            candidate = TimetableState(assignments=new_assignments)
        else:
            candidate = random_neighbor(state, instance)
    else:
        i, j = random.sample(range(n), 2)
        new_assignments = list(assignments)
        a = new_assignments[i]
        b = new_assignments[j]
        new_assignments[i] = LectureAssignment(a.course_id, b.room_id, b.day, b.period)
        new_assignments[j] = LectureAssignment(b.course_id, a.room_id, a.day, a.period)
        candidate = TimetableState(assignments=new_assignments)
    evaluate_timetable(candidate, instance)
    candidates.append(
        (
            candidate,
            int(candidate.hard_violations or 0),
            float(candidate.soft_penalty or 0.0),
        )
    )
    return candidates


def _roulette_select(
    candidates: list[TimetableState],
    weights: list[float],
) -> TimetableState:
    total = sum(weights)
    if total <= 0.0:
        return random.choice(candidates)
    pick = random.uniform(0.0, total)
    acc = 0.0
    for candidate, weight in zip(candidates, weights):
        acc += weight
        if pick <= acc:
            return candidate
    return candidates[-1]


def _deposit_solution(
    pheromone: dict[PheromoneKey, float],
    state: TimetableState,
    amount: float,
) -> None:
    for lecture_index, assignment in enumerate(state.assignments):
        if assignment.room_id is None or assignment.day is None or assignment.period is None:
            continue
        key = (lecture_index, assignment.room_id, assignment.day, assignment.period)
        pheromone[key] = pheromone.get(key, PHEROMONE_MIN) + amount


def _clamp_pheromone(pheromone: dict[PheromoneKey, float]) -> None:
    for key in pheromone:
        val = pheromone[key]
        if val < PHEROMONE_MIN:
            pheromone[key] = PHEROMONE_MIN
        elif val > PHEROMONE_MAX:
            pheromone[key] = PHEROMONE_MAX


def initialize_aco_state(
    instance: ITCInstance,
    *,
    starting_state: TimetableState | None = None,
) -> ACOState:
    """Initialize ACO once and return persistent ant-colony state."""
    n_lectures = sum(c.lectures_per_week for c in instance.courses)
    pheromone = _init_pheromone(instance, n_lectures)
    if starting_state is not None:
        base_state = starting_state.copy()
        evaluate_timetable(base_state, instance)
    else:
        base_state = generate_initial_solution(instance)
    best_solution = base_state.copy()
    best_fitness = float(best_solution.fitness or 0.0)
    return ACOState(
        pheromone=pheromone,
        best_solution=best_solution,
        best_fitness=best_fitness,
        base_state=base_state.copy(),
    )


def run_aco_with_state(
    instance: ITCInstance,
    state: ACOState,
    *,
    iterations: int = 30,
    num_ants: int = 5,
    alpha: float = 1.0,
    beta: float = 2.0,
    evaporation_rate: float = 0.1,
    verbose: bool = False,
    early_stop_patience: int | None = None,
) -> tuple[ACOState, TimetableState, list[float]]:
    """Continue ACO for a few iterations from an existing persistent state."""
    slots_by_course = feasible_slots_by_course(instance)
    history: list[float] = []
    base_state = (
        state.base_state.copy()
        if state.base_state is not None
        else state.best_solution.copy()
    )

    for iter_in_call in range(1, iterations + 1):
        iteration_best: TimetableState | None = None
        iteration_best_fitness = float("inf")
        iteration_best_hard = int(state.best_solution.hard_violations or 0)

        for _ in range(num_ants):
            ant_state = base_state.copy()
            diversity_steps = ANT_START_DIVERSITY_STEPS
            if state.stagnation_counter >= STAGNATION_EXTRA_DIVERSITY_TRIGGER:
                diversity_steps += STAGNATION_EXTRA_DIVERSITY_STEPS
            for _ in range(diversity_steps):
                ant_state = random_neighbor(ant_state, instance)
            conflict_set = get_conflicting_lectures(ant_state, instance)
            ant_fitness = float(ant_state.fitness or 0.0)
            if ant_fitness < iteration_best_fitness:
                iteration_best_fitness = ant_fitness
                iteration_best = ant_state
                iteration_best_hard = int(ant_state.hard_violations or 0)

            for lecture_index in _priority_lecture_indices(ant_state, instance):
                candidates = _candidates_for_lecture(
                    ant_state,
                    instance,
                    lecture_index,
                    slots_by_course,
                    prioritize_conflict=lecture_index in conflict_set,
                )
                weights: list[float] = []
                current_hard = int(ant_state.hard_violations or 0)
                current_soft = float(ant_state.soft_penalty or 0.0)

                for candidate, cand_hard, cand_soft in candidates:
                    key = _pheromone_key(lecture_index, candidate)
                    tau = (
                        state.pheromone.get(key, PHEROMONE_MIN)
                        if key is not None
                        else PHEROMONE_MIN
                    )
                    eta = _heuristic(current_hard, current_soft, cand_hard, cand_soft)
                    weights.append((tau**alpha) * (eta**beta))

                candidate_states = [cand[0] for cand in candidates]
                ant_state = _roulette_select(candidate_states, weights)
                ant_fitness = float(ant_state.fitness or 0.0)
                if ant_fitness < iteration_best_fitness:
                    iteration_best_fitness = ant_fitness
                    iteration_best = ant_state
                    iteration_best_hard = int(ant_state.hard_violations or 0)

            ant_state = repair_conflicts(
                ant_state, instance, max_attempts=REPAIR_ATTEMPTS_PER_ANT
            )
            ant_fitness = float(ant_state.fitness or 0.0)
            if ant_fitness < iteration_best_fitness:
                iteration_best_fitness = ant_fitness
                iteration_best = ant_state
                iteration_best_hard = int(ant_state.hard_violations or 0)

        for key in state.pheromone:
            state.pheromone[key] *= 1.0 - evaporation_rate

        if iteration_best is not None:
            global_hard = int(state.best_solution.hard_violations or 0)
            hard_gain = max(0, global_hard - iteration_best_hard)
            if hard_gain > 0:
                deposit = (DEPOSIT_Q * (1.0 + 2.0 * hard_gain)) / max(
                    iteration_best_fitness, 1.0
                )
            else:
                deposit = (DEPOSIT_Q * 0.05) / max(iteration_best_fitness, 1.0)
            _deposit_solution(state.pheromone, iteration_best, deposit)

            if iteration_best_fitness < state.best_fitness:
                state.best_fitness = iteration_best_fitness
                state.best_solution = iteration_best
                state.stagnation_counter = 0
                state.no_improve_iters = 0
            else:
                state.stagnation_counter += 1
                state.no_improve_iters += 1

        _clamp_pheromone(state.pheromone)

        if state.stagnation_counter >= STAGNATION_PHEROMONE_RESET_TRIGGER:
            for key in state.pheromone:
                state.pheromone[key] = PHEROMONE_BASELINE
            state.stagnation_counter = 0

        if state.stagnation_counter >= RUIN_STAGNATION_TRIGGER:
            best_ruin = state.best_solution
            best_ruin_fit = float(state.best_solution.fitness or float("inf"))
            for _ in range(RUIN_ATTEMPTS):
                ruined = ruin_and_recreate(
                    state.best_solution,
                    instance,
                    lectures_to_ruin=RUIN_LECTURES,
                    repair_attempts=REPAIR_ATTEMPTS_PER_ANT,
                )
                ruined_fit = float(ruined.fitness or float("inf"))
                if ruined_fit < best_ruin_fit:
                    best_ruin = ruined
                    best_ruin_fit = ruined_fit
            base_state = best_ruin
        else:
            base_state = state.best_solution.copy()
        state.base_state = base_state.copy()

        history.append(state.best_fitness)
        state.iteration_count += 1

        if verbose and iter_in_call % 5 == 0:
            print(f"Iteration {iter_in_call}/{iterations}: Best Fitness = {state.best_fitness}")

        if early_stop_patience is not None and state.no_improve_iters >= early_stop_patience:
            break

    return state, state.best_solution, history


def run_aco(
    instance: ITCInstance,
    iterations: int = 30,
    num_ants: int = 5,
    alpha: float = 1.0,
    beta: float = 2.0,
    evaporation_rate: float = 0.1,
    *,
    verbose: bool = False,
    starting_state: TimetableState | None = None,
    early_stop_patience: int | None = None,
) -> tuple[TimetableState, list[float]]:
    """Runs the ACO metaheuristic and returns the best state found along with its convergence history."""
    state = initialize_aco_state(instance, starting_state=starting_state)
    state, best, history = run_aco_with_state(
        instance,
        state,
        iterations=iterations,
        num_ants=num_ants,
        alpha=alpha,
        beta=beta,
        evaporation_rate=evaporation_rate,
        verbose=verbose,
        early_stop_patience=early_stop_patience,
    )
    return best, history