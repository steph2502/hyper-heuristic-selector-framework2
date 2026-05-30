"""Simple hill-climbing local search on timetabling states."""

from __future__ import annotations

from algorithms.fitness import evaluate_timetable
from algorithms.neighborhood import random_neighbor
from models.timetable import TimetableState
from parsers.itc_parser import ITCInstance


def hill_climb(
    initial_state: TimetableState,
    instance: ITCInstance,
    max_iterations: int = 1000,
    *,
    feasible_soft_refinement_iters: int = 100,
) -> tuple[TimetableState, list[float]]:
    """Greedy hill climb using :func:`random_neighbor` moves/swap proposals.

    At each iteration a neighbor is generated (shallow-copy semantics inside
    ``random_neighbor``). The move is **accepted** if
    ``neighbor.fitness <= current_state.fitness`` (non-strict improvement,
    allowing sideways steps on plateaus). The **global best** is tracked whenever
    ``current_state`` strictly improves in fitness.

    ``history[k]`` stores ``best_state.fitness`` after iteration ``k`` (0-based),
    suitable for convergence plots.

    **Early stop:** once ``best_state.hard_violations == 0``, if
    ``feasible_soft_refinement_iters > 0``, the search continues until that many
    consecutive iterations have passed with a feasible best (soft polishing).
    If ``feasible_soft_refinement_iters`` is ``0``, the loop ends at
    ``max_iterations`` even when feasible.

    Args:
        initial_state: Starting solution (typically from ``generate_initial_solution``).
            If ``fitness`` is ``None``, it is evaluated in place once.
        instance: Parsed ITC instance.
        max_iterations: Number of iterations while the best solution is still
            **infeasible** (``hard_violations > 0``). Once feasible, up to
            ``feasible_soft_refinement_iters`` additional consecutive feasible
            iterations may run beyond this bound.
        feasible_soft_refinement_iters: Consecutive-feasible-iterations tail;
            set to ``0`` in unit tests to cap run length.

    Returns:
        ``(best_state, history)`` where ``history`` has one entry per executed
        iteration.
    """
    if initial_state.fitness is None:
        evaluate_timetable(initial_state, instance)

    current_state = initial_state
    best_state = initial_state
    history: list[float] = []

    consecutive_feasible_iters = 0
    cap = max_iterations + feasible_soft_refinement_iters + 10

    for i in range(cap):
        neighbor = random_neighbor(current_state, instance)

        if neighbor.fitness <= current_state.fitness:
            current_state = neighbor

        if current_state.fitness < best_state.fitness:
            best_state = current_state

        history.append(float(best_state.fitness))

        it = i + 1
        if it % 100 == 0:
            print(f"Iteration {it}: Current Best Fitness = {best_state.fitness}")

        if best_state.hard_violations == 0:
            if feasible_soft_refinement_iters > 0:
                consecutive_feasible_iters += 1
                if consecutive_feasible_iters >= feasible_soft_refinement_iters:
                    break
        else:
            consecutive_feasible_iters = 0

        if i >= max_iterations - 1 and (
            best_state.hard_violations > 0 or feasible_soft_refinement_iters == 0
        ):
            break

    return best_state, history
