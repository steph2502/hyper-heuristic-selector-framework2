"""ITC timetabler CLI (Phase 1: parse + optional fitness smoke check)."""

from __future__ import annotations

import argparse
import json
import time
import sys
from pathlib import Path

from algorithms.aco import run_aco
from algorithms.controller import run_hyper_heuristic
from algorithms.pso import run_pso
from algorithms.fitness import evaluate_timetable
from algorithms.initializer import count_scheduled_lectures, generate_initial_solution
from algorithms.local_search import hill_climb
from models.timetable import TimetableState
from parsers.itc_parser import ITCInstance, parse_itc_file
from utils.timetable_output import export_timetable_csv, print_timetable


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ITC 2007 timetabling (Phase 1: parse & models)")
    parser.add_argument("instance", type=Path, help="Path to ITC .txt instance")
    parser.add_argument(
        "--summary-json",
        action="store_true",
        help="Print a JSON summary of parsed counts and dimensions",
    )
    parser.add_argument(
        "--empty-fitness",
        action="store_true",
        help="Evaluate fitness of an empty timetable (sanity check)",
    )
    parser.add_argument(
        "--generate-initial",
        action="store_true",
        help="Greedy construction of an initial timetable, then evaluate and print metrics",
    )
    parser.add_argument(
        "--run-local",
        action="store_true",
        help="Hill-climb local search from greedy initializer (prints before/after metrics)",
    )
    parser.add_argument(
        "--run-aco",
        action="store_true",
        help="Ant Colony Optimisation from greedy starts (prints fitness metrics and history)",
    )
    parser.add_argument(
        "--run-pso",
        action="store_true",
        help="Discrete PSO from greedy starts (prints fitness metrics and history)",
    )
    parser.add_argument(
        "--run-controller",
        action="store_true",
        help="Selection hyper-heuristic controller over ACO/PSO bursts",
    )
    parser.add_argument(
        "--run-best",
        action="store_true",
        help="Run greedy, ACO, PSO, and controller then export the best timetable found",
    )
    parser.add_argument(
        "--export-timetable",
        action="store_true",
        help="Print and export the final best timetable to CSV",
    )
    args = parser.parse_args(argv)

    inst = parse_itc_file(args.instance)
    if args.summary_json:
        summary = {
            "name": inst.name,
            "nr_courses": len(inst.courses),
            "nr_rooms": len(inst.rooms),
            "nr_curricula": len(inst.curricula),
            "nr_unavailability_constraints": sum(len(u.forbidden_slots) for u in inst.unavailability),
            "nr_days": inst.nr_days,
            "periods_per_day": inst.periods_per_day,
            "nr_lecturers": len(inst.lecturers),
        }
        print(json.dumps(summary, indent=2))
        return 0

    print(f"Parsed {inst.name}: {len(inst.courses)} courses, {len(inst.rooms)} rooms, {inst.nr_days}x{inst.periods_per_day}")
    if args.run_aco:
        started = time.perf_counter()
        initial = generate_initial_solution(inst)
        init_fit = float(initial.fitness)  # type: ignore[arg-type]
        best, history = run_aco(inst, verbose=True)
        final_fit = float(best.fitness)  # type: ignore[arg-type]
        elapsed = time.perf_counter() - started
        print(f"Initial Fitness (from greedy initializer): {init_fit}")
        print(f"Final Fitness: {final_fit}")
        print(f"Final Hard Violations: {best.hard_violations}")
        print(f"Final Soft Penalty: {best.soft_penalty}")
        print(f"Full iteration history length: {len(history)}")
        print(f"Runtime (seconds): {elapsed:.2f}")
        _maybe_export_timetable(args.export_timetable, best, inst)
    elif args.run_pso:
        started = time.perf_counter()
        initial = generate_initial_solution(inst)
        init_fit = float(initial.fitness)  # type: ignore[arg-type]
        best, history = run_pso(inst, verbose=True)
        final_fit = float(best.fitness)  # type: ignore[arg-type]
        elapsed = time.perf_counter() - started
        print(f"Initial Fitness (from greedy initializer): {init_fit}")
        print(f"Final DPSO Fitness: {final_fit}")
        print(f"Final Hard Violations: {best.hard_violations}")
        print(f"Final Soft Penalty: {best.soft_penalty}")
        print(f"Full iteration history length: {len(history)}")
        print(f"Runtime (seconds): {elapsed:.2f}")
        _maybe_export_timetable(args.export_timetable, best, inst)
    elif args.run_controller:
        started = time.perf_counter()
        initial = generate_initial_solution(inst)
        init_fit = float(initial.fitness)  # type: ignore[arg-type]
        best, history, stats = run_hyper_heuristic(inst)
        final_fit = float(best.fitness)  # type: ignore[arg-type]
        elapsed = time.perf_counter() - started
        print(f"Initial Fitness (from greedy initializer): {init_fit}")
        print(f"Selected heuristics across iterations: {stats['selection_history']}")
        print(f"Final Fitness: {final_fit}")
        print(f"Final Hard Violations: {best.hard_violations}")
        print(f"Final Soft Penalty: {best.soft_penalty}")
        print(f"Controller iterations completed: {len(history)}")
        print(f"Runtime (seconds): {elapsed:.2f}")
        print(
            "Heuristic usage counts: "
            f"ACO={stats['ACO']['times_used']}, PSO={stats['PSO']['times_used']}"
        )
        _maybe_export_timetable(args.export_timetable, best, inst)
    elif args.run_best:
        started = time.perf_counter()
        print("Running all four conditions to find best timetable...")

        results: list[tuple[float, str, TimetableState]] = []

        greedy = generate_initial_solution(inst)
        evaluate_timetable(greedy, inst)
        results.append((float(greedy.fitness or float("inf")), "Greedy", greedy))
        print(f"Greedy:     fitness={greedy.fitness}, hard={greedy.hard_violations}")

        aco_state, _ = run_aco(inst, iterations=30, num_ants=5, verbose=False)
        evaluate_timetable(aco_state, inst)
        results.append((float(aco_state.fitness or float("inf")), "ACO", aco_state))
        print(f"ACO:        fitness={aco_state.fitness}, hard={aco_state.hard_violations}")

        pso_state, _ = run_pso(inst, iterations=30, num_particles=5, verbose=False)
        evaluate_timetable(pso_state, inst)
        results.append((float(pso_state.fitness or float("inf")), "PSO", pso_state))
        print(f"PSO:        fitness={pso_state.fitness}, hard={pso_state.hard_violations}")

        ctrl_state, _, _ = run_hyper_heuristic(inst)
        evaluate_timetable(ctrl_state, inst)
        results.append((float(ctrl_state.fitness or float("inf")), "Controller", ctrl_state))
        print(f"Controller: fitness={ctrl_state.fitness}, hard={ctrl_state.hard_violations}")

        best_fitness, best_label, best_state = min(results, key=lambda x: x[0])
        elapsed = time.perf_counter() - started

        print(
            f"\nBest result: {best_label} with fitness={best_fitness:.2f}, "
            f"hard={best_state.hard_violations}, soft={best_state.soft_penalty}"
        )
        print(f"Total runtime (seconds): {elapsed:.2f}")
        _maybe_export_timetable(True, best_state, inst)
    elif args.run_local:
        initial = generate_initial_solution(inst)
        init_fit = float(initial.fitness)  # type: ignore[arg-type]
        init_hard = int(initial.hard_violations)  # type: ignore[arg-type]
        best, history = hill_climb(initial, inst, max_iterations=1000)
        final_fit = float(best.fitness)  # type: ignore[arg-type]
        final_hard = int(best.hard_violations)  # type: ignore[arg-type]
        print(f"Initial fitness: {init_fit}  ->  Final (best) fitness: {final_fit}")
        print(f"Initial hard violations: {init_hard}  ->  Final hard violations: {final_hard}")
        if init_fit > 0:
            pct = (init_fit - final_fit) / init_fit * 100.0
            print(f"Improvement (fitness): {pct:.2f}%")
        else:
            print("Improvement (fitness): n/a (initial fitness was 0)")
        print(f"Hill-climb iterations recorded: {len(history)}")
    elif args.generate_initial:
        state = generate_initial_solution(inst)
        scheduled, total = count_scheduled_lectures(state)
        print(f"Hard violations: {state.hard_violations}")
        print(f"Soft penalty: {state.soft_penalty}")
        print(f"Total fitness: {state.fitness}")
        print(f"Scheduled lectures: {scheduled} / {total}")
    elif args.empty_fitness:
        state = TimetableState.from_course_list(inst.courses)
        evaluate_timetable(state, inst)
        print(
            f"Empty timetable fitness: {state.fitness} "
            f"(hard={state.hard_violations}, soft={state.soft_penalty})"
        )
    return 0


def _maybe_export_timetable(
    should_export: bool,
    state: TimetableState,
    instance: ITCInstance,
) -> None:
    if not should_export:
        return
    print_timetable(state, instance)
    saved = export_timetable_csv(state, instance, Path("results") / "final_timetable.csv")
    print(f"Timetable CSV saved to: {saved}")


if __name__ == "__main__":
    raise SystemExit(main())
