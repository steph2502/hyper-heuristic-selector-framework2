"""Discrete Particle Swarm Optimization for ITC timetabling."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TypeAlias

from algorithms.fitness import evaluate_timetable
from algorithms.initializer import generate_initial_solution
from algorithms.neighborhood import move_lecture, random_neighbor
from algorithms.repair import get_conflicting_lectures, repair_conflicts, ruin_and_recreate
from models.timetable import LectureAssignment, TimetableState
from parsers.itc_parser import ITCInstance

VelocityMove: TypeAlias = tuple[int, str, int, int]

DIVERSITY_NEIGHBORS = 3
STAGNATION_LIMIT = 5
STAGNATION_MUTATION_STEPS = 3
REPAIR_ATTEMPTS_PER_PARTICLE = 8
RUIN_STAGNATION_TRIGGER = 8
RUIN_LECTURES = 8


@dataclass
class Particle:
    """One swarm member with discrete position and move-list velocity."""

    position: TimetableState
    velocity: list[VelocityMove]
    pbest: TimetableState
    no_improve_iters: int = 0


@dataclass
class PSOState:
    """Persistent PSO state used by stateful controller bursts."""

    particles: list[Particle]
    gbest: TimetableState
    gbest_fitness: float
    iteration_count: int = 0
    stagnation_counter: int = 0
    no_improve_iters: int = 0
    baseline_state: TimetableState | None = None


def _slots_differ(a: LectureAssignment, b: LectureAssignment) -> bool:
    return (a.room_id, a.day, a.period) != (b.room_id, b.day, b.period)


def _move_toward_target(lecture_index: int, target: LectureAssignment) -> VelocityMove | None:
    if target.room_id is None or target.day is None or target.period is None:
        return None
    return (lecture_index, target.room_id, target.day, target.period)


def _update_velocity(
    particle: Particle,
    gbest: TimetableState,
    instance: ITCInstance,
    *,
    w: float,
    c1: float,
    c2: float,
) -> list[VelocityMove]:
    """Rebuild velocity from inertia, cognitive, and social move components."""
    n_lectures = len(particle.position.assignments)
    prev = particle.velocity
    velocity: list[VelocityMove] = []

    if prev:
        n_inertia = max(1, int(w * len(prev)))
        k = min(n_inertia, len(prev))
        velocity.extend(random.sample(prev, k))

    conflict_indices = list(get_conflicting_lectures(particle.position, instance))
    if conflict_indices:
        index_pool = conflict_indices
    else:
        index_pool = list(range(n_lectures))

    cognitive_indices = [
        i
        for i in index_pool
        if _slots_differ(particle.position.assignments[i], particle.pbest.assignments[i])
    ]
    n_cognitive = max(1, int(c1 * n_lectures))
    if cognitive_indices:
        for idx in random.sample(cognitive_indices, min(n_cognitive, len(cognitive_indices))):
            move = _move_toward_target(idx, particle.pbest.assignments[idx])
            if move is not None:
                velocity.append(move)

    social_indices = [
        i
        for i in index_pool
        if _slots_differ(particle.position.assignments[i], gbest.assignments[i])
    ]
    n_social = max(1, int(c2 * n_lectures))
    if social_indices:
        for idx in random.sample(social_indices, min(n_social, len(social_indices))):
            move = _move_toward_target(idx, gbest.assignments[idx])
            if move is not None:
                velocity.append(move)

    if int(particle.position.hard_violations or 0) > 0:
        for idx in conflict_indices:
            move = _move_toward_target(idx, particle.pbest.assignments[idx])
            if move is not None:
                velocity.append(move)

    max_velocity_len = 2 * n_lectures
    if len(velocity) > max_velocity_len:
        velocity = velocity[:max_velocity_len]

    return velocity


def _apply_velocity(
    position: TimetableState,
    velocity: list[VelocityMove],
    instance: ITCInstance,
) -> TimetableState:
    """Apply each velocity move; explore with random_neighbor when velocity is empty."""
    state = position
    for lecture_index, room_id, day, period in velocity:
        state = move_lecture(state, instance, lecture_index, room_id, day, period)
    if not velocity:
        state = random_neighbor(state, instance)
    return state


def _seed_particle(base_state: TimetableState, instance: ITCInstance) -> TimetableState:
    state = base_state.copy()
    for _ in range(DIVERSITY_NEIGHBORS):
        state = random_neighbor(state, instance)
    return state


def _init_swarm(
    base_state: TimetableState,
    instance: ITCInstance,
    num_particles: int,
) -> list[Particle]:
    particles: list[Particle] = []
    for _ in range(num_particles):
        position = _seed_particle(base_state, instance)
        pbest = position.copy()
        particles.append(Particle(position=position, velocity=[], pbest=pbest))
    return particles


def initialize_pso_state(
    instance: ITCInstance,
    *,
    num_particles: int = 5,
    initial_state: TimetableState | None = None,
    starting_state: TimetableState | None = None,
) -> PSOState:
    """Initialize PSO once and return persistent swarm state."""
    warm_start = starting_state if starting_state is not None else initial_state
    if warm_start is not None:
        base_state = warm_start.copy()
        evaluate_timetable(base_state, instance)
    else:
        base_state = generate_initial_solution(instance)
    particles = _init_swarm(base_state, instance, max(1, num_particles))
    gbest = min(particles, key=lambda p: float(p.position.fitness or 0.0)).pbest.copy()
    gbest_fitness = float(gbest.fitness or 0.0)
    return PSOState(
        particles=particles,
        gbest=gbest,
        gbest_fitness=gbest_fitness,
        baseline_state=base_state.copy(),
    )


def _ensure_swarm_size(state: PSOState, instance: ITCInstance, num_particles: int) -> None:
    target = max(1, num_particles)
    current = len(state.particles)
    if current == target:
        return
    if current > target:
        state.particles = state.particles[:target]
        return

    seed_state = state.gbest.copy()
    needed = target - current
    for _ in range(needed):
        position = _seed_particle(seed_state, instance)
        pbest = position.copy()
        state.particles.append(Particle(position=position, velocity=[], pbest=pbest))


def run_pso_with_state(
    instance: ITCInstance,
    state: PSOState,
    *,
    iterations: int = 30,
    num_particles: int | None = None,
    w: float = 0.4,
    c1: float = 2.0,
    c2: float = 0.3,
    verbose: bool = False,
    early_stop_patience: int | None = None,
) -> tuple[PSOState, TimetableState, list[float]]:
    """Continue PSO for a few iterations from an existing persistent state."""
    if num_particles is not None:
        _ensure_swarm_size(state, instance, num_particles)
    particles = state.particles
    history: list[float] = []

    for iter_in_call in range(1, iterations + 1):
        for particle in particles:
            prev_assignments = particle.position.assignments
            particle.velocity = _update_velocity(
                particle,
                state.gbest,
                instance,
                w=w,
                c1=c1,
                c2=c2,
            )
            particle.position = _apply_velocity(particle.position, particle.velocity, instance)
            no_change = particle.position.assignments == prev_assignments
            particle.position = repair_conflicts(
                particle.position, instance, max_attempts=REPAIR_ATTEMPTS_PER_PARTICLE
            )

            pos_fit = float(particle.position.fitness or 0.0)
            pbest_fit = float(particle.pbest.fitness or 0.0)
            if pos_fit < pbest_fit:
                particle.pbest = particle.position.copy()
                particle.no_improve_iters = 0
            else:
                particle.no_improve_iters += 1

            if no_change or particle.no_improve_iters >= STAGNATION_LIMIT:
                for _ in range(STAGNATION_MUTATION_STEPS):
                    particle.position = random_neighbor(particle.position, instance)
                particle.position = repair_conflicts(
                    particle.position, instance, max_attempts=REPAIR_ATTEMPTS_PER_PARTICLE
                )
                pos_fit = float(particle.position.fitness or 0.0)
                if pos_fit < float(particle.pbest.fitness or 0.0):
                    particle.pbest = particle.position.copy()
                    particle.no_improve_iters = 0

            if pos_fit < state.gbest_fitness:
                state.gbest_fitness = pos_fit
                state.gbest = particle.position.copy()
                state.stagnation_counter = 0

        history.append(state.gbest_fitness)

        if all(float(p.position.fitness or 0.0) >= state.gbest_fitness for p in particles):
            state.stagnation_counter += 1
            state.no_improve_iters += 1
        else:
            state.no_improve_iters = 0

        if state.stagnation_counter >= RUIN_STAGNATION_TRIGGER:
            state.gbest = ruin_and_recreate(
                state.gbest,
                instance,
                lectures_to_ruin=RUIN_LECTURES,
                repair_attempts=REPAIR_ATTEMPTS_PER_PARTICLE,
            )
            state.gbest_fitness = float(state.gbest.fitness or state.gbest_fitness)
            state.stagnation_counter = 0

        state.iteration_count += 1

        if verbose and iter_in_call % 10 == 0:
            print(
                f"Iteration {iter_in_call}/{iterations}: "
                f"Swarm Best Fitness = {state.gbest_fitness}"
            )

        if early_stop_patience is not None and state.no_improve_iters >= early_stop_patience:
            break

    baseline = state.baseline_state.copy() if state.baseline_state is not None else state.gbest.copy()
    evaluate_timetable(baseline, instance)
    baseline_fitness = float(baseline.fitness or 0.0)
    if state.gbest_fitness > baseline_fitness:
        state.gbest = baseline
        state.gbest_fitness = baseline_fitness
        return state, baseline, history
    return state, state.gbest, history


def run_pso(
    instance: ITCInstance,
    iterations: int = 30,
    num_particles: int = 5,
    w: float = 0.4,
    c1: float = 2.0,
    c2: float = 0.3,
    *,
    verbose: bool = False,
    initial_state: TimetableState | None = None,
    starting_state: TimetableState | None = None,
    early_stop_patience: int | None = None,
) -> tuple[TimetableState, list[float]]:
    """Runs the Discrete PSO metaheuristic and returns the best state found along with its convergence history."""
    state = initialize_pso_state(
        instance,
        num_particles=num_particles,
        initial_state=initial_state,
        starting_state=starting_state,
    )
    state, best, history = run_pso_with_state(
        instance,
        state,
        iterations=iterations,
        num_particles=num_particles,
        w=w,
        c1=c1,
        c2=c2,
        verbose=verbose,
        early_stop_patience=early_stop_patience,
    )
    return best, history
