from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
EXP02 = ROOT / "experiments" / "exp02_full_quantitative_benchmarks"
EXP = ROOT / "experiments" / "exp03_retrieval_reconstruction_baselines"
FULL_CSV = EXP02 / "full_quantitative_benchmark.csv"
FIGURES = EXP / "figures"
SEED = 20260701


FEATURE_SETS = {
    "pattern": [
        "panel_count",
        "pattern_edge_count",
        "stitch_count",
        "pattern_components",
        "mean_panel_area",
        "total_panel_area",
        "mean_panel_perimeter",
        "curved_edge_count",
        "parameter_count",
    ],
    "mesh": [
        "sim_vertices",
        "sim_faces",
        "sim_boundary_edges",
        "sim_components",
        "sim_mean_edge_length",
        "sim_mean_triangle_area",
        "sim_mean_aspect_ratio",
        "scan_vertices",
        "scan_faces",
        "scan_boundary_edges",
        "scan_components",
        "scan_mean_edge_length",
        "scan_mean_triangle_area",
        "scan_mean_aspect_ratio",
    ],
    "segmentation": [
        "sim_seg_label_count",
        "sim_seg_panel_label_count",
        "sim_seg_stitch_fraction",
        "sim_seg_entropy",
        "scan_seg_label_count",
        "scan_seg_panel_label_count",
        "scan_seg_stitch_fraction",
        "scan_seg_entropy",
    ],
}
FEATURE_SETS["combined"] = FEATURE_SETS["pattern"] + FEATURE_SETS["mesh"] + FEATURE_SETS["segmentation"]


def font(size: int, bold: bool = False):
    candidates = ("arialbd.ttf", "calibrib.ttf") if bold else ("arial.ttf", "calibri.ttf")
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def read_rows() -> list[dict]:
    with FULL_CSV.open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def value(row: dict, key: str) -> float:
    try:
        out = float(row.get(key, 0) or 0)
    except ValueError:
        out = 0.0
    if not math.isfinite(out):
        return 0.0
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def make_splits(rows: list[dict]) -> dict[str, str]:
    rng = random.Random(SEED)
    by_category: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_category[row["category"]].append(row)

    split_map: dict[str, str] = {}
    split_rows = []
    for category, items in sorted(by_category.items()):
        items = items[:]
        rng.shuffle(items)
        n = len(items)
        n_train = int(round(n * 0.70))
        n_val = int(round(n * 0.15))
        for i, row in enumerate(items):
            split = "train" if i < n_train else "val" if i < n_train + n_val else "test"
            split_map[row["sample_id"]] = split
            split_rows.append({"category": category, "sample_id": row["sample_id"], "split": split})
    write_csv(EXP / "splits.csv", split_rows)
    return split_map


def matrix(rows: list[dict], features: list[str]) -> np.ndarray:
    return np.asarray([[value(row, key) for key in features] for row in rows], dtype=np.float64)


def standardize(train: np.ndarray, test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = train.mean(axis=0, keepdims=True)
    std = train.std(axis=0, keepdims=True)
    std[std < 1e-9] = 1.0
    return (train - mean) / std, (test - mean) / std


def evaluate_nn(name: str, train_rows: list[dict], test_rows: list[dict], features: list[str]) -> dict:
    train_x, test_x = standardize(matrix(train_rows, features), matrix(test_rows, features))
    train_labels = np.asarray([row["category"] for row in train_rows])
    test_labels = np.asarray([row["category"] for row in test_rows])
    train_panels = np.asarray([value(row, "panel_count") for row in train_rows])
    train_stitches = np.asarray([value(row, "stitch_count") for row in train_rows])
    test_panels = np.asarray([value(row, "panel_count") for row in test_rows])
    test_stitches = np.asarray([value(row, "stitch_count") for row in test_rows])

    top1 = top5 = 0
    rr_total = 0.0
    panel_abs = []
    stitch_abs = []
    confusion: Counter[tuple[str, str]] = Counter()
    batch = 256
    train_norm = np.sum(train_x * train_x, axis=1, keepdims=True).T
    for start in range(0, len(test_rows), batch):
        end = min(start + batch, len(test_rows))
        q = test_x[start:end]
        dists = np.sum(q * q, axis=1, keepdims=True) + train_norm - 2 * q @ train_x.T
        k = min(20, train_x.shape[0])
        idx = np.argpartition(dists, kth=k - 1, axis=1)[:, :k]
        sorted_local = np.take_along_axis(idx, np.argsort(np.take_along_axis(dists, idx, axis=1), axis=1), axis=1)
        for local_i, neighbors in enumerate(sorted_local):
            true = test_labels[start + local_i]
            pred = train_labels[neighbors[0]]
            top1 += int(pred == true)
            top5 += int(true in set(train_labels[neighbors[:5]]))
            rank = next((r + 1 for r, nb in enumerate(neighbors) if train_labels[nb] == true), None)
            rr_total += 1.0 / rank if rank else 0.0
            panel_abs.append(abs(train_panels[neighbors[0]] - test_panels[start + local_i]))
            stitch_abs.append(abs(train_stitches[neighbors[0]] - test_stitches[start + local_i]))
            confusion[(true, pred)] += 1

    n = len(test_rows)
    confusion_rows = [
        {"feature_set": name, "true_category": true, "pred_category": pred, "count": count}
        for (true, pred), count in sorted(confusion.items())
    ]
    write_csv(EXP / f"confusion_{name}.csv", confusion_rows)
    return {
        "baseline": f"nn_{name}",
        "features": len(features),
        "test_samples": n,
        "top1": top1 / n,
        "top5": top5 / n,
        "mrr": rr_total / n,
        "panel_mae": float(np.mean(panel_abs)),
        "stitch_mae": float(np.mean(stitch_abs)),
    }


def random_and_majority(train_rows: list[dict], test_rows: list[dict]) -> list[dict]:
    train_labels = [row["category"] for row in train_rows]
    test_labels = [row["category"] for row in test_rows]
    counts = Counter(train_labels)
    majority = counts.most_common(1)[0][0]
    rng = random.Random(SEED)
    categories = sorted(counts)
    random_top1 = sum(rng.choice(categories) == label for label in test_labels) / len(test_labels)
    majority_top1 = sum(majority == label for label in test_labels) / len(test_labels)
    majority_top5_set = {cat for cat, _ in counts.most_common(5)}
    return [
        {
            "baseline": "random_category",
            "features": 0,
            "test_samples": len(test_rows),
            "top1": random_top1,
            "top5": min(5 / len(categories), 1.0),
            "mrr": 0.0,
            "panel_mae": 0.0,
            "stitch_mae": 0.0,
        },
        {
            "baseline": "majority_category",
            "features": 0,
            "test_samples": len(test_rows),
            "top1": majority_top1,
            "top5": sum(label in majority_top5_set for label in test_labels) / len(test_labels),
            "mrr": 0.0,
            "panel_mae": 0.0,
            "stitch_mae": 0.0,
        },
    ]


def split_summary(rows: list[dict], split_map: dict[str, str]) -> list[dict]:
    counts: Counter[tuple[str, str]] = Counter()
    for row in rows:
        counts[(row["category"], split_map[row["sample_id"]])] += 1
    out = []
    for category in sorted({row["category"] for row in rows}):
        item = {"category": category}
        for split in ("train", "val", "test"):
            item[split] = counts[(category, split)]
        item["total"] = sum(item[split] for split in ("train", "val", "test"))
        out.append(item)
    return out


def draw_baseline_chart(rows: list[dict]) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = [row for row in rows if row["baseline"].startswith("nn_")]
    width, height = 1600, 920
    margin_l, margin_r, margin_t, margin_b = 170, 90, 135, 150
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((margin_l, 45), "Retrieval baseline performance", fill=(20, 24, 28), font=font(44, True))
    draw.line((margin_l, margin_t, margin_l, margin_t + plot_h), fill=(30, 30, 30), width=3)
    draw.line((margin_l, margin_t + plot_h, margin_l + plot_w, margin_t + plot_h), fill=(30, 30, 30), width=3)
    for tick in range(6):
        y = margin_t + plot_h - int(plot_h * tick / 5)
        draw.line((margin_l - 8, y, margin_l + plot_w, y), fill=(226, 229, 232), width=1)
        draw.text((margin_l - 80, y - 14), f"{tick/5:.1f}", fill=(80, 84, 88), font=font(24))
    colors = [(44, 123, 182), (247, 147, 30), (93, 164, 101)]
    metrics = [("top1", "top-1"), ("top5", "top-5"), ("mrr", "MRR")]
    group_w = plot_w / len(rows)
    bar_w = group_w / 5
    for i, row in enumerate(rows):
        base_x = margin_l + i * group_w + group_w * 0.18
        for j, (key, _) in enumerate(metrics):
            h = int(plot_h * float(row[key]))
            x0 = int(base_x + j * bar_w)
            draw.rounded_rectangle((x0, margin_t + plot_h - h, x0 + int(bar_w * 0.8), margin_t + plot_h), radius=5, fill=colors[j])
        label = row["baseline"].replace("nn_", "")
        draw.text((int(margin_l + i * group_w + 20), margin_t + plot_h + 25), label, fill=(30, 34, 38), font=font(28))
    lx, ly = margin_l + plot_w - 360, 60
    for i, (_, label) in enumerate(metrics):
        draw.rounded_rectangle((lx, ly, lx + 32, ly + 22), radius=4, fill=colors[i])
        draw.text((lx + 44, ly - 6), label, fill=(50, 54, 58), font=font(28))
        ly += 38
    path = FIGURES / "fig_retrieval_baselines.png"
    image.save(path, quality=95)
    return path


def write_report(results: list[dict], split_rows: list[dict]) -> None:
    lines = [
        "# Retrieval and Reconstruction Baseline Report",
        "",
        "This experiment uses the full quantitative feature table to create stratified train/validation/test splits and evaluate nearest-neighbor retrieval baselines. The retrieved neighbor is also treated as a simple reconstruction baseline for predicting panel and stitch counts.",
        "",
        "## Split Summary",
        "",
        "| Category | Train | Val | Test | Total |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in split_rows:
        lines.append(f"| `{row['category']}` | {row['train']} | {row['val']} | {row['test']} | {row['total']} |")
    lines += [
        "",
        "## Baseline Results",
        "",
        "| Baseline | Features | Test N | Top-1 | Top-5 | MRR | Panel MAE | Stitch MAE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| `{row['baseline']}` | {row['features']} | {row['test_samples']} | "
            f"{row['top1']:.4f} | {row['top5']:.4f} | {row['mrr']:.4f} | "
            f"{row['panel_mae']:.4f} | {row['stitch_mae']:.4f} |"
        )
    (EXP / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    EXP.mkdir(parents=True, exist_ok=True)
    rows = read_rows()
    split_map = make_splits(rows)
    split_rows = split_summary(rows, split_map)
    write_csv(EXP / "split_summary.csv", split_rows)
    train_rows = [row for row in rows if split_map[row["sample_id"]] == "train"]
    test_rows = [row for row in rows if split_map[row["sample_id"]] == "test"]
    results = random_and_majority(train_rows, test_rows)
    for name, features in FEATURE_SETS.items():
        results.append(evaluate_nn(name, train_rows, test_rows, features))
    write_csv(EXP / "baseline_results.csv", results)
    draw_baseline_chart(results)
    write_report(results, split_rows)
    (EXP / "summary.json").write_text(
        json.dumps(
            {
                "seed": SEED,
                "train": len(train_rows),
                "test": len(test_rows),
                "baselines": len(results),
                "best_top1": max(float(row["top1"]) for row in results),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"train": len(train_rows), "test": len(test_rows), "baselines": len(results)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
