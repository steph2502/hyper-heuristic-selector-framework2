"""Algorithms package (ACO/PSO/controller/repair are reserved for later phases)."""

from algorithms.aco import run_aco
from algorithms.controller import (
    extract_features,
    run_hyper_heuristic,
    score_aco,
    score_pso,
    select_heuristic,
)
from algorithms.pso import run_pso
from algorithms.fitness import FitnessResult, evaluate_fitness, evaluate_timetable
from algorithms.initializer import count_scheduled_lectures, generate_initial_solution
from algorithms.local_search import hill_climb
from algorithms.neighborhood import move_lecture, random_neighbor, swap_lectures
from algorithms.repair import get_conflicting_lectures, repair_conflicts

__all__ = [
    "FitnessResult",
    "evaluate_fitness",
    "evaluate_timetable",
    "run_aco",
    "run_pso",
    "extract_features",
    "score_aco",
    "score_pso",
    "select_heuristic",
    "run_hyper_heuristic",
    "generate_initial_solution",
    "count_scheduled_lectures",
    "hill_climb",
    "move_lecture",
    "random_neighbor",
    "swap_lectures",
    "get_conflicting_lectures",
    "repair_conflicts",
]
