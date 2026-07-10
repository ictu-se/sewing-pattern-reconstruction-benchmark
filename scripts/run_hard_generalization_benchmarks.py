from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
EXP02 = ROOT / "experiments" / "exp02_full_quantitative_benchmarks"
EXP03 = ROOT / "experiments" / "exp03_retrieval_reconstruction_baselines"
EXP04 = ROOT / "experiments" / "exp04_render_image_retrieval_baselines"
EXP = ROOT / "experiments" / "exp06_hard_generalization_benchmarks"
FIGURES = EXP / "figures"
FULL_CSV = EXP02 / "full_quantitative_benchmark.csv"
SPLITS_CSV = EXP03 / "splits.csv"
FEATURE_NPZ = EXP04 / "render_features.npz"
FEATURE_META_CSV = EXP04 / "render_feature_metadata.csv"
SEED = 20260710


STRUCTURED_FEATURES = [
    "panel_count",
    "pattern_edge_count",
    "stitch_count",
    "pattern_components",
    "mean_panel_area",
    "total_panel_area",
    "mean_panel_perimeter",
    "curved_edge_count",
    "parameter_count",
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
    "sim_seg_label_count",
    "sim_seg_panel_label_count",
    "sim_seg_stitch_fraction",
    "sim_seg_entropy",
    "scan_seg_label_count",
    "scan_seg_panel_label_count",
    "scan_seg_stitch_fraction",
    "scan_seg_entropy",
]


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def font(size: int, bold: bool = False):
    candidates = ("arialbd.ttf", "calibrib.ttf") if bold else ("arial.ttf", "calibri.ttf")
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def short(category: str) -> str:
    return {
        "dress_sleeveless_2550": "dress",
        "jacket_2200": "jacket",
        "jacket_hood_2700": "hood",
        "jumpsuit_sleeveless_2000": "jumpsuit",
        "pants_straight_sides_1000": "pants",
        "skirt_2_panels_1200": "skirt-2",
        "skirt_4_panels_1600": "skirt-4",
        "skirt_8_panels_1000": "skirt-8",
        "tee_2300": "tee",
        "tee_sleeveless_1800": "tee-s",
        "wb_dress_sleeveless_2600": "wb-d",
        "wb_pants_straight_1500": "wb-p",
    }.get(category, category)


def family(category: str) -> str:
    if "dress" in category:
        return "dress"
    if "jacket" in category:
        return "jacket"
    if "pants" in category or "skirt" in category:
        return "lower-body"
    if "tee" in category:
        return "upper-body"
    if "jumpsuit" in category:
        return "jumpsuit"
    return category.split("_", 1)[0]


def value(row: dict, key: str) -> float:
    try:
        out = float(row.get(key, 0) or 0)
    except ValueError:
        out = 0.0
    return out if math.isfinite(out) else 0.0


def structured_matrix(rows: list[dict]) -> np.ndarray:
    return np.asarray([[value(row, key) for key in STRUCTURED_FEATURES] for row in rows], dtype=np.float32)


def standardize(train: np.ndarray, test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = train.mean(axis=0, keepdims=True)
    std = train.std(axis=0, keepdims=True)
    std[std < 1e-6] = 1.0
    return ((train - mean) / std).astype(np.float32), ((test - mean) / std).astype(np.float32)


def nearest_neighbor_metrics(train_x: np.ndarray, test_x: np.ndarray, train_rows: list[dict], test_rows: list[dict]) -> dict:
    train_x, test_x = standardize(train_x, test_x)
    train_labels = np.asarray([row["category"] for row in train_rows])
    test_labels = np.asarray([row["category"] for row in test_rows])
    train_families = np.asarray([family(row["category"]) for row in train_rows])
    test_families = np.asarray([family(row["category"]) for row in test_rows])
    train_panels = np.asarray([value(row, "panel_count") for row in train_rows], dtype=np.float32)
    train_stitches = np.asarray([value(row, "stitch_count") for row in train_rows], dtype=np.float32)
    test_panels = np.asarray([value(row, "panel_count") for row in test_rows], dtype=np.float32)
    test_stitches = np.asarray([value(row, "stitch_count") for row in test_rows], dtype=np.float32)

    top1 = 0
    family_hit = 0
    exact_panel = 0
    exact_stitch = 0
    panel_abs: list[float] = []
    stitch_abs: list[float] = []
    confusion: Counter[tuple[str, str]] = Counter()
    batch = 192
    train_norm = np.sum(train_x * train_x, axis=1, keepdims=True).T
    for start in range(0, len(test_rows), batch):
        end = min(start + batch, len(test_rows))
        query = test_x[start:end]
        dists = np.sum(query * query, axis=1, keepdims=True) + train_norm - 2 * query @ train_x.T
        winners = np.argmin(dists, axis=1)
        for local_i, winner in enumerate(winners):
            absolute_i = start + local_i
            true = test_labels[absolute_i]
            pred = train_labels[winner]
            top1 += int(pred == true)
            family_hit += int(train_families[winner] == test_families[absolute_i])
            exact_panel += int(train_panels[winner] == test_panels[absolute_i])
            exact_stitch += int(train_stitches[winner] == test_stitches[absolute_i])
            panel_abs.append(abs(float(train_panels[winner] - test_panels[absolute_i])))
            stitch_abs.append(abs(float(train_stitches[winner] - test_stitches[absolute_i])))
            confusion[(true, pred)] += 1
    n = len(test_rows)
    return {
        "test_samples": n,
        "top1": top1 / n,
        "family_hit": family_hit / n,
        "panel_exact": exact_panel / n,
        "stitch_exact": exact_stitch / n,
        "panel_mae": float(np.mean(panel_abs)),
        "stitch_mae": float(np.mean(stitch_abs)),
        "confusion": confusion,
    }


def leave_one_category_out(rows: list[dict], feature_name: str, features: np.ndarray, row_order: list[dict]) -> list[dict]:
    index = {row["sample_id"]: i for i, row in enumerate(row_order)}
    results = []
    categories = sorted({row["category"] for row in rows})
    for category in categories:
        train_rows = [row for row in rows if row["category"] != category]
        test_rows = [row for row in rows if row["category"] == category]
        train_idx = np.asarray([index[row["sample_id"]] for row in train_rows], dtype=np.int64)
        test_idx = np.asarray([index[row["sample_id"]] for row in test_rows], dtype=np.int64)
        metrics = nearest_neighbor_metrics(features[train_idx], features[test_idx], train_rows, test_rows)
        results.append(
            {
                "protocol": "leave_one_category_out",
                "feature_set": feature_name,
                "held_out_category": category,
                "train_samples": len(train_rows),
                "test_samples": len(test_rows),
                "top1": metrics["top1"],
                "family_hit": metrics["family_hit"],
                "panel_exact": metrics["panel_exact"],
                "stitch_exact": metrics["stitch_exact"],
                "panel_mae": metrics["panel_mae"],
                "stitch_mae": metrics["stitch_mae"],
            }
        )
    return results


def paired_transfer(rows: list[dict], feature_name: str, features: np.ndarray, row_order: list[dict]) -> list[dict]:
    pairs = [
        ("dress_sleeveless_2550", "wb_dress_sleeveless_2600"),
        ("pants_straight_sides_1000", "wb_pants_straight_1500"),
        ("jacket_2200", "jacket_hood_2700"),
        ("tee_2300", "tee_sleeveless_1800"),
        ("skirt_2_panels_1200", "skirt_4_panels_1600"),
        ("skirt_4_panels_1600", "skirt_8_panels_1000"),
    ]
    index = {row["sample_id"]: i for i, row in enumerate(row_order)}
    results = []
    for source, target in pairs:
        train_rows = [row for row in rows if row["category"] == source]
        test_rows = [row for row in rows if row["category"] == target]
        if not train_rows or not test_rows:
            continue
        train_idx = np.asarray([index[row["sample_id"]] for row in train_rows], dtype=np.int64)
        test_idx = np.asarray([index[row["sample_id"]] for row in test_rows], dtype=np.int64)
        metrics = nearest_neighbor_metrics(features[train_idx], features[test_idx], train_rows, test_rows)
        results.append(
            {
                "protocol": "paired_transfer",
                "feature_set": feature_name,
                "source_category": source,
                "target_category": target,
                "train_samples": len(train_rows),
                "test_samples": len(test_rows),
                "family_hit": metrics["family_hit"],
                "panel_exact": metrics["panel_exact"],
                "stitch_exact": metrics["stitch_exact"],
                "panel_mae": metrics["panel_mae"],
                "stitch_mae": metrics["stitch_mae"],
            }
        )
    return results


def render_noise_stress(features: np.ndarray, meta: list[dict], split_map: dict[str, str]) -> list[dict]:
    rng = np.random.default_rng(SEED)
    index = {row["sample_id"]: i for i, row in enumerate(meta)}
    train_rows = [row for row in meta if split_map[row["sample_id"]] == "train"]
    test_rows = [row for row in meta if split_map[row["sample_id"]] == "test"]
    train_idx = np.asarray([index[row["sample_id"]] for row in train_rows], dtype=np.int64)
    test_idx = np.asarray([index[row["sample_id"]] for row in test_rows], dtype=np.int64)
    train_x = features[train_idx]
    test_clean = features[test_idx]
    rows = []
    for sigma in (0.0, 0.05, 0.10, 0.20, 0.35):
        noisy = test_clean.copy()
        if sigma:
            noisy += rng.normal(0.0, sigma, size=noisy.shape).astype(np.float32)
        metrics = nearest_neighbor_metrics(train_x, noisy, train_rows, test_rows)
        rows.append(
            {
                "protocol": "render_noise_stress",
                "feature_set": "render_pair",
                "noise_sigma": sigma,
                "train_samples": len(train_rows),
                "test_samples": len(test_rows),
                "top1": metrics["top1"],
                "family_hit": metrics["family_hit"],
                "panel_exact": metrics["panel_exact"],
                "stitch_exact": metrics["stitch_exact"],
                "panel_mae": metrics["panel_mae"],
                "stitch_mae": metrics["stitch_mae"],
            }
        )
    return rows


def draw_loco_chart(rows: list[dict]) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    render_rows = [row for row in rows if row["feature_set"] == "render_pair"]
    width, height = 1800, 980
    left, right, top, bottom = 155, 80, 135, 180
    plot_w = width - left - right
    plot_h = height - top - bottom
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((left, 45), "Leave-one-category-out generalization", fill=(20, 24, 28), font=font(44, True))
    draw.line((left, top, left, top + plot_h), fill=(30, 30, 30), width=3)
    draw.line((left, top + plot_h, left + plot_w, top + plot_h), fill=(30, 30, 30), width=3)
    for tick in range(6):
        y = top + plot_h - int(plot_h * tick / 5)
        draw.line((left - 8, y, left + plot_w, y), fill=(226, 229, 232), width=1)
        draw.text((left - 75, y - 14), f"{tick / 5:.1f}", fill=(80, 84, 88), font=font(24))
    metrics = [("family_hit", "family", (41, 121, 140)), ("panel_exact", "panel", (231, 142, 64)), ("stitch_exact", "stitch", (116, 101, 162))]
    group_w = plot_w / len(render_rows)
    bar_w = group_w / 4.6
    for i, row in enumerate(render_rows):
        base_x = left + i * group_w + group_w * 0.12
        for j, (key, _, color) in enumerate(metrics):
            h = int(plot_h * float(row[key]))
            x0 = int(base_x + j * bar_w)
            draw.rounded_rectangle((x0, top + plot_h - h, x0 + int(bar_w * 0.8), top + plot_h), radius=4, fill=color)
        draw.text((int(left + i * group_w + 5), top + plot_h + 25), short(row["held_out_category"]), fill=(35, 39, 43), font=font(23))
    lx, ly = left + plot_w - 360, 60
    for _, label, color in metrics:
        draw.rounded_rectangle((lx, ly, lx + 32, ly + 22), radius=4, fill=color)
        draw.text((lx + 44, ly - 6), label, fill=(50, 54, 58), font=font(28))
        ly += 38
    path = FIGURES / "fig_leave_one_category_out.png"
    image.save(path, quality=95)
    return path


def draw_noise_chart(rows: list[dict]) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    width, height = 1500, 900
    left, right, top, bottom = 150, 90, 130, 135
    plot_w = width - left - right
    plot_h = height - top - bottom
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((left, 45), "Render descriptor noise stress test", fill=(20, 24, 28), font=font(44, True))
    draw.line((left, top, left, top + plot_h), fill=(30, 30, 30), width=3)
    draw.line((left, top + plot_h, left + plot_w, top + plot_h), fill=(30, 30, 30), width=3)
    for tick in range(6):
        y = top + plot_h - int(plot_h * tick / 5)
        draw.line((left - 8, y, left + plot_w, y), fill=(226, 229, 232), width=1)
        draw.text((left - 75, y - 14), f"{tick / 5:.1f}", fill=(80, 84, 88), font=font(24))
    series = [("top1", "top-1", (41, 121, 140)), ("family_hit", "family", (116, 101, 162)), ("panel_exact", "panel", (231, 142, 64))]
    xs = [left + int(plot_w * i / (len(rows) - 1)) for i in range(len(rows))]
    for key, label, color in series:
        points = [(xs[i], top + plot_h - int(plot_h * float(row[key]))) for i, row in enumerate(rows)]
        draw.line(points, fill=color, width=5)
        for x, y in points:
            draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=color)
    for i, row in enumerate(rows):
        draw.text((xs[i] - 28, top + plot_h + 25), f"{float(row['noise_sigma']):.2f}", fill=(35, 39, 43), font=font(24))
    draw.text((left + plot_w // 2 - 70, top + plot_h + 80), "noise sigma", fill=(80, 84, 88), font=font(26, True))
    lx, ly = left + plot_w - 300, 62
    for _, label, color in series:
        draw.line((lx, ly + 12, lx + 34, ly + 12), fill=color, width=5)
        draw.text((lx + 48, ly - 5), label, fill=(50, 54, 58), font=font(28))
        ly += 40
    path = FIGURES / "fig_render_noise_stress.png"
    image.save(path, quality=95)
    return path


def write_report(loco_rows: list[dict], transfer_rows: list[dict], noise_rows: list[dict]) -> None:
    def avg(rows: list[dict], key: str) -> float:
        return sum(float(row[key]) for row in rows) / max(len(rows), 1)

    render_loco = [row for row in loco_rows if row["feature_set"] == "render_pair"]
    structured_loco = [row for row in loco_rows if row["feature_set"] == "structured"]
    lines = [
        "# Hard Generalization Benchmark Report",
        "",
        "This experiment adds harder protocols to the original random stratified split. The goal is to separate easy category recognition from genuine cross-category structural transfer.",
        "",
        "## Protocols",
        "",
        "- `leave_one_category_out`: train on all categories except one held-out category; evaluate family match and structural reconstruction proxies.",
        "- `paired_transfer`: train on one related category and test on its paired variant, such as base pants to waistband pants.",
        "- `render_noise_stress`: keep the original train/test split but perturb deterministic render descriptors at test time.",
        "",
        "## Aggregate Findings",
        "",
        "| Protocol | Feature Set | Mean Family Hit | Mean Panel Exact | Mean Stitch Exact | Mean Panel MAE | Mean Stitch MAE |",
        "|---|---|---:|---:|---:|---:|---:|",
        f"| leave-one-category-out | structured | {avg(structured_loco, 'family_hit'):.4f} | {avg(structured_loco, 'panel_exact'):.4f} | {avg(structured_loco, 'stitch_exact'):.4f} | {avg(structured_loco, 'panel_mae'):.4f} | {avg(structured_loco, 'stitch_mae'):.4f} |",
        f"| leave-one-category-out | render_pair | {avg(render_loco, 'family_hit'):.4f} | {avg(render_loco, 'panel_exact'):.4f} | {avg(render_loco, 'stitch_exact'):.4f} | {avg(render_loco, 'panel_mae'):.4f} | {avg(render_loco, 'stitch_mae'):.4f} |",
        "",
        "## Leave-One-Category-Out Results",
        "",
        "| Feature Set | Held-Out Category | Test N | Family Hit | Panel Exact | Stitch Exact | Panel MAE | Stitch MAE |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in loco_rows:
        lines.append(
            f"| `{row['feature_set']}` | `{row['held_out_category']}` | {row['test_samples']} | "
            f"{float(row['family_hit']):.4f} | {float(row['panel_exact']):.4f} | {float(row['stitch_exact']):.4f} | "
            f"{float(row['panel_mae']):.4f} | {float(row['stitch_mae']):.4f} |"
        )
    lines += [
        "",
        "## Paired Transfer Results",
        "",
        "| Feature Set | Source | Target | Family Hit | Panel Exact | Stitch Exact | Panel MAE | Stitch MAE |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in transfer_rows:
        lines.append(
            f"| `{row['feature_set']}` | `{row['source_category']}` | `{row['target_category']}` | "
            f"{float(row['family_hit']):.4f} | {float(row['panel_exact']):.4f} | {float(row['stitch_exact']):.4f} | "
            f"{float(row['panel_mae']):.4f} | {float(row['stitch_mae']):.4f} |"
        )
    lines += [
        "",
        "## Render Noise Stress",
        "",
        "| Noise Sigma | Top-1 | Family Hit | Panel Exact | Stitch Exact | Panel MAE | Stitch MAE |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in noise_rows:
        lines.append(
            f"| {float(row['noise_sigma']):.2f} | {float(row['top1']):.4f} | {float(row['family_hit']):.4f} | "
            f"{float(row['panel_exact']):.4f} | {float(row['stitch_exact']):.4f} | "
            f"{float(row['panel_mae']):.4f} | {float(row['stitch_mae']):.4f} |"
        )
    (EXP / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    EXP.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = read_csv(FULL_CSV)
    split_map = {row["sample_id"]: row["split"] for row in read_csv(SPLITS_CSV)}
    render_meta = read_csv(FEATURE_META_CSV)
    render_features = np.load(FEATURE_NPZ)["features"].astype(np.float32)
    row_by_id = {row["sample_id"]: row for row in rows}
    ordered_full_rows = [row_by_id[row["sample_id"]] for row in rows]
    structured_features = structured_matrix(ordered_full_rows)
    render_full_rows = [row_by_id[row["sample_id"]] for row in render_meta]

    loco_rows = []
    loco_rows.extend(leave_one_category_out(ordered_full_rows, "structured", structured_features, ordered_full_rows))
    loco_rows.extend(leave_one_category_out(render_full_rows, "render_pair", render_features, render_full_rows))
    transfer_rows = []
    transfer_rows.extend(paired_transfer(ordered_full_rows, "structured", structured_features, ordered_full_rows))
    transfer_rows.extend(paired_transfer(render_full_rows, "render_pair", render_features, render_full_rows))
    noise_rows = render_noise_stress(render_features, render_meta, split_map)

    write_csv(EXP / "leave_one_category_out.csv", loco_rows)
    write_csv(EXP / "paired_transfer.csv", transfer_rows)
    write_csv(EXP / "render_noise_stress.csv", noise_rows)
    draw_loco_chart(loco_rows)
    draw_noise_chart(noise_rows)
    write_report(loco_rows, transfer_rows, noise_rows)
    summary = {
        "seed": SEED,
        "samples": len(rows),
        "render_samples": len(render_meta),
        "protocols": ["leave_one_category_out", "paired_transfer", "render_noise_stress"],
        "leave_one_category_out_rows": len(loco_rows),
        "paired_transfer_rows": len(transfer_rows),
        "noise_stress_rows": len(noise_rows),
        "render_noise_top1_clean": noise_rows[0]["top1"],
        "render_noise_top1_sigma_035": noise_rows[-1]["top1"],
    }
    (EXP / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
