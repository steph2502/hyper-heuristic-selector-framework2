"""Generate convergence plots from benchmark convergence JSON."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

INPUT_PATH = Path("results") / "convergence_histories.json"
OUTPUT_DIR = Path("results") / "figures"
TARGET_METHODS = ("ACO", "PSO", "Controller")


def _pad_history(history: list[float], length: int) -> list[float]:
    if not history:
        return [0.0] * length
    if len(history) >= length:
        return history[:length]
    tail = history[-1]
    return history + [tail] * (length - len(history))


def _mean_curve(histories: list[list[float]]) -> list[float]:
    if not histories:
        return []
    max_len = max(len(h) for h in histories)
    padded = [_pad_history(h, max_len) for h in histories]
    means: list[float] = []
    for i in range(max_len):
        means.append(sum(h[i] for h in padded) / len(padded))
    return means


def main() -> int:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing input JSON: {INPUT_PATH}")

    payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    entries = payload.get("entries", [])
    by_dataset: dict[str, dict[str, list[list[float]]]] = {}

    for entry in entries:
        method = str(entry.get("method", ""))
        if method not in TARGET_METHODS:
            continue
        dataset = str(entry.get("dataset_name", "unknown_dataset"))
        history_raw = entry.get("convergence_history", [])
        if not isinstance(history_raw, list):
            continue
        history = [float(x) for x in history_raw]
        by_dataset.setdefault(dataset, {}).setdefault(method, []).append(history)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for dataset_name, method_histories in by_dataset.items():
        plt.figure(figsize=(8, 5))
        for method in TARGET_METHODS:
            histories = method_histories.get(method, [])
            if not histories:
                continue
            curve = _mean_curve(histories)
            if not curve:
                continue
            iterations = list(range(1, len(curve) + 1))
            plt.plot(iterations, curve, label=method)

        plt.title(f"Convergence Comparison - {dataset_name}")
        plt.xlabel("Iteration")
        plt.ylabel("Best Fitness")
        plt.legend()
        plt.grid(True, linestyle="--", linewidth=0.5, alpha=0.6)
        safe_name = "".join(
            ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in dataset_name
        ).strip("_") or "dataset"
        out_path = OUTPUT_DIR / f"convergence_{safe_name}.png"
        plt.tight_layout()
        plt.savefig(out_path, dpi=150)
        plt.close()
        print(f"Saved figure: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
