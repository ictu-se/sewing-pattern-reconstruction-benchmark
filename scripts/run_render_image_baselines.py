from __future__ import annotations

import csv
import json
import math
import random
import time
import zipfile
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ARCHIVES = ROOT / "raw" / "zenodo_3d_garments_sewing_patterns" / "archives"
EXP02 = ROOT / "experiments" / "exp02_full_quantitative_benchmarks"
EXP03 = ROOT / "experiments" / "exp03_retrieval_reconstruction_baselines"
EXP = ROOT / "experiments" / "exp04_render_image_retrieval_baselines"
FIGURES = EXP / "figures"
FULL_CSV = EXP02 / "full_quantitative_benchmark.csv"
SPLITS_CSV = EXP03 / "splits.csv"
SEED = 20260701
VIEW_FEATURE_DIM = 375


def log(message: str) -> None:
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), message, flush=True)


def font(size: int, bold: bool = False):
    candidates = ("arialbd.ttf", "calibrib.ttf") if bold else ("arial.ttf", "calibri.ttf")
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


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


def short(name: str) -> str:
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
    }.get(name, name)


def image_feature(raw: bytes | None) -> np.ndarray:
    if raw is None:
        return np.zeros(VIEW_FEATURE_DIM, dtype=np.float32)
    try:
        image = Image.open(BytesIO(raw)).convert("RGB")
    except Exception:
        return np.zeros(VIEW_FEATURE_DIM, dtype=np.float32)
    image = image.resize((48, 48), Image.Resampling.LANCZOS)
    rgb = np.asarray(image, dtype=np.float32) / 255.0
    gray_img = image.convert("L").resize((16, 16), Image.Resampling.LANCZOS)
    gray = np.asarray(gray_img, dtype=np.float32).reshape(-1) / 255.0
    edges = np.asarray(gray_img.filter(ImageFilter.FIND_EDGES), dtype=np.float32).reshape(-1) / 255.0
    hist_parts = []
    for channel in range(3):
        hist, _ = np.histogram(rgb[:, :, channel], bins=16, range=(0.0, 1.0))
        hist = hist.astype(np.float32)
        hist_parts.append(hist / max(float(hist.sum()), 1.0))
    mean = rgb.mean(axis=(0, 1))
    std = rgb.std(axis=(0, 1))
    return np.concatenate([gray, edges[:64], *hist_parts, mean, std, np.ones(1, dtype=np.float32)]).astype(np.float32)


def paired_feature(front: bytes | None, back: bytes | None) -> np.ndarray:
    f = image_feature(front)
    b = image_feature(back)
    return np.concatenate([f, b, np.abs(f - b)]).astype(np.float32)


def archive_category(path: Path) -> str:
    return path.name.removesuffix(".zip")


def sample_folder(name: str) -> str:
    return name.split("/", 1)[0]


def build_features(rows: list[dict]) -> tuple[np.ndarray, list[dict]]:
    feature_path = EXP / "render_features.npz"
    meta_path = EXP / "render_feature_metadata.csv"
    if feature_path.exists() and meta_path.exists():
        log("Loading cached render features")
        meta = read_csv(meta_path)
        data = np.load(feature_path)
        return data["features"].astype(np.float32), meta

    EXP.mkdir(parents=True, exist_ok=True)
    by_category: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in rows:
        by_category[row["category"]][row["sample_id"]] = row

    features: list[np.ndarray] = []
    meta: list[dict] = []
    for archive in sorted(path for path in ARCHIVES.glob("*.zip") if path.name != "test.zip"):
        category = archive_category(archive)
        wanted = by_category.get(category, {})
        if not wanted:
            continue
        log(f"Opening {archive.name} for render features")
        with zipfile.ZipFile(archive) as zf:
            names_by_folder: dict[str, list[str]] = defaultdict(list)
            for name in zf.namelist():
                if "/" in name and not name.endswith("/"):
                    folder = sample_folder(name)
                    if folder in wanted:
                        names_by_folder[folder].append(name)
            total = len(names_by_folder)
            for index, sample_id in enumerate(sorted(wanted), start=1):
                if index % 500 == 0:
                    log(f"{archive.name}: image features {index}/{total}")
                names = names_by_folder.get(sample_id, [])
                front_name = next((name for name in names if name.endswith("_camera_front.png")), None)
                back_name = next((name for name in names if name.endswith("_camera_back.png")), None)
                front = zf.read(front_name) if front_name else None
                back = zf.read(back_name) if back_name else None
                row = wanted[sample_id]
                features.append(paired_feature(front, back))
                meta.append(
                    {
                        "category": category,
                        "sample_id": sample_id,
                        "has_front": int(front_name is not None),
                        "has_back": int(back_name is not None),
                        "panel_count": row["panel_count"],
                        "stitch_count": row["stitch_count"],
                    }
                )

    matrix = np.vstack(features).astype(np.float32)
    np.savez_compressed(feature_path, features=matrix)
    write_csv(meta_path, meta)
    log(f"Wrote {feature_path}")
    log(f"Wrote {meta_path}")
    return matrix, meta


def standardize(train: np.ndarray, test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = train.mean(axis=0, keepdims=True)
    std = train.std(axis=0, keepdims=True)
    std[std < 1e-6] = 1.0
    return ((train - mean) / std).astype(np.float32), ((test - mean) / std).astype(np.float32)


def evaluate_nn(train_x: np.ndarray, test_x: np.ndarray, train_rows: list[dict], test_rows: list[dict], name: str) -> dict:
    train_x, test_x = standardize(train_x, test_x)
    train_labels = np.asarray([row["category"] for row in train_rows])
    test_labels = np.asarray([row["category"] for row in test_rows])
    train_panels = np.asarray([float(row["panel_count"]) for row in train_rows], dtype=np.float32)
    train_stitches = np.asarray([float(row["stitch_count"]) for row in train_rows], dtype=np.float32)
    test_panels = np.asarray([float(row["panel_count"]) for row in test_rows], dtype=np.float32)
    test_stitches = np.asarray([float(row["stitch_count"]) for row in test_rows], dtype=np.float32)

    top1 = top5 = 0
    rr_total = 0.0
    panel_abs = []
    stitch_abs = []
    confusion: Counter[tuple[str, str]] = Counter()
    examples_by_category: dict[str, dict] = {}
    error_examples: list[dict] = []
    batch = 192
    train_norm = np.sum(train_x * train_x, axis=1, keepdims=True).T
    for start in range(0, len(test_rows), batch):
        end = min(start + batch, len(test_rows))
        q = test_x[start:end]
        dists = np.sum(q * q, axis=1, keepdims=True) + train_norm - 2 * q @ train_x.T
        k = min(20, train_x.shape[0])
        idx = np.argpartition(dists, kth=k - 1, axis=1)[:, :k]
        sorted_local = np.take_along_axis(idx, np.argsort(np.take_along_axis(dists, idx, axis=1), axis=1), axis=1)
        for local_i, neighbors in enumerate(sorted_local):
            absolute_i = start + local_i
            true = test_labels[absolute_i]
            pred = train_labels[neighbors[0]]
            top1 += int(pred == true)
            top5 += int(true in set(train_labels[neighbors[:5]]))
            rank = next((r + 1 for r, nb in enumerate(neighbors) if train_labels[nb] == true), None)
            rr_total += 1.0 / rank if rank else 0.0
            panel_abs.append(abs(train_panels[neighbors[0]] - test_panels[absolute_i]))
            stitch_abs.append(abs(train_stitches[neighbors[0]] - test_stitches[absolute_i]))
            confusion[(true, pred)] += 1
            example = {
                "query_category": true,
                "query_sample_id": test_rows[absolute_i]["sample_id"],
                "retrieved_category": pred,
                "retrieved_sample_id": train_rows[neighbors[0]]["sample_id"],
                "rank_true_category": rank or 0,
                "distance": float(dists[local_i, neighbors[0]]),
                "is_error": 0,
            }
            if pred == true and true not in examples_by_category:
                examples_by_category[true] = example
            elif pred != true and len(error_examples) < 24:
                error_examples.append(
                    {
                        **example,
                        "is_error": 1,
                    }
                )
    n = len(test_rows)
    confusion_rows = [
        {"baseline": name, "true_category": true, "pred_category": pred, "count": count}
        for (true, pred), count in sorted(confusion.items())
    ]
    write_csv(EXP / f"confusion_{name}.csv", confusion_rows)
    examples = list(examples_by_category.values()) + error_examples
    write_csv(EXP / f"retrieval_examples_{name}.csv", examples)
    return {
        "baseline": name,
        "features": train_x.shape[1],
        "train_samples": len(train_rows),
        "test_samples": n,
        "top1": top1 / n,
        "top5": top5 / n,
        "mrr": rr_total / n,
        "panel_mae": float(np.mean(panel_abs)),
        "stitch_mae": float(np.mean(stitch_abs)),
    }


def confusion_heatmap(name: str) -> Path:
    rows = read_csv(EXP / f"confusion_{name}.csv")
    cats = sorted({row["true_category"] for row in rows} | {row["pred_category"] for row in rows})
    idx = {cat: i for i, cat in enumerate(cats)}
    matrix = [[0 for _ in cats] for _ in cats]
    for row in rows:
        matrix[idx[row["true_category"]]][idx[row["pred_category"]]] += int(row["count"])
    row_sums = [sum(row) or 1 for row in matrix]
    cell = 72
    left, top = 310, 170
    width, height = left + cell * len(cats) + 90, top + cell * len(cats) + 230
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((left, 45), f"Confusion heatmap: {name}", fill=(20, 24, 28), font=font(44, True))
    draw.text((34, top - 54), "true", fill=(90, 94, 98), font=font(28, True))
    draw.text((left, top + cell * len(cats) + 90), "predicted", fill=(90, 94, 98), font=font(28, True))
    for i, cat in enumerate(cats):
        draw.text((34, top + i * cell + 20), short(cat), fill=(35, 39, 43), font=font(24))
        draw.text((left + i * cell + 6, top + cell * len(cats) + 22), short(cat), fill=(35, 39, 43), font=font(22))
    for r in range(len(cats)):
        for c in range(len(cats)):
            v = matrix[r][c] / row_sums[r]
            shade = int(245 - 180 * v)
            x0, y0 = left + c * cell, top + r * cell
            draw.rectangle((x0, y0, x0 + cell - 2, y0 + cell - 2), fill=(shade, shade + 5 if shade < 245 else shade, 255))
            if v >= 0.08:
                draw.text((x0 + 13, y0 + 23), f"{v:.2f}", fill=(20, 24, 28), font=font(20, True))
    path = FIGURES / f"fig_confusion_{name}.png"
    image.save(path, quality=95)
    return path


def baseline_chart(results: list[dict]) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    width, height = 1600, 920
    margin_l, margin_r, margin_t, margin_b = 170, 90, 135, 170
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((margin_l, 45), "Image-to-pattern retrieval baselines", fill=(20, 24, 28), font=font(44, True))
    draw.line((margin_l, margin_t, margin_l, margin_t + plot_h), fill=(30, 30, 30), width=3)
    draw.line((margin_l, margin_t + plot_h, margin_l + plot_w, margin_t + plot_h), fill=(30, 30, 30), width=3)
    for tick in range(6):
        y = margin_t + plot_h - int(plot_h * tick / 5)
        draw.line((margin_l - 8, y, margin_l + plot_w, y), fill=(226, 229, 232), width=1)
        draw.text((margin_l - 80, y - 14), f"{tick/5:.1f}", fill=(80, 84, 88), font=font(24))
    metrics = [("top1", "top-1", (44, 123, 182)), ("top5", "top-5", (247, 147, 30)), ("mrr", "MRR", (93, 164, 101))]
    group_w = plot_w / len(results)
    bar_w = group_w / 5
    for i, row in enumerate(results):
        base_x = margin_l + i * group_w + group_w * 0.18
        for j, (key, _, color) in enumerate(metrics):
            h = int(plot_h * float(row[key]))
            x0 = int(base_x + j * bar_w)
            draw.rounded_rectangle((x0, margin_t + plot_h - h, x0 + int(bar_w * 0.8), margin_t + plot_h), radius=5, fill=color)
        draw.text((int(margin_l + i * group_w + 5), margin_t + plot_h + 26), row["baseline"].replace("nn_", ""), fill=(30, 34, 38), font=font(26))
    lx, ly = margin_l + plot_w - 340, 60
    for _, label, color in metrics:
        draw.rounded_rectangle((lx, ly, lx + 32, ly + 22), radius=4, fill=color)
        draw.text((lx + 44, ly - 6), label, fill=(50, 54, 58), font=font(28))
        ly += 38
    path = FIGURES / "fig_image_retrieval_baselines.png"
    image.save(path, quality=95)
    return path


def image_from_archive(sample_id: str, suffix: str) -> Image.Image | None:
    category = next((archive for archive in ARCHIVES.glob("*.zip") if sample_id.startswith(archive.stem.rsplit("_", 1)[0])), None)
    # Fallback: sample folders are unique, so search archive stems by prefix family.
    archives = sorted(path for path in ARCHIVES.glob("*.zip") if path.name != "test.zip")
    for archive in archives:
        if not sample_id.startswith(archive.stem.split("_", 1)[0]):
            continue
        try:
            with zipfile.ZipFile(archive) as zf:
                prefix = f"{sample_id}/"
                name = next((item for item in zf.namelist() if item.startswith(prefix) and item.endswith(suffix)), None)
                if name:
                    return Image.open(BytesIO(zf.read(name))).convert("RGB")
        except Exception:
            continue
    return None


def find_archive_for_sample(sample_id: str) -> Path | None:
    for archive in sorted(path for path in ARCHIVES.glob("*.zip") if path.name != "test.zip"):
        with zipfile.ZipFile(archive) as zf:
            if any(name.startswith(f"{sample_id}/") for name in zf.namelist()[:50]):
                return archive
    return None


def make_qualitative_grid(meta_by_id: dict[str, dict]) -> Path:
    examples = read_csv(EXP / "retrieval_examples_nn_render_pair.csv")
    selected = [row for row in examples if row["query_category"] == row["retrieved_category"]][:8]
    if len(selected) < 8:
        selected = examples[:8]

    width, height = 1700, 1280
    tile_w, tile_h = 190, 190
    row_h = 250
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((60, 40), "Render-to-pattern nearest-neighbor examples", fill=(20, 24, 28), font=font(42, True))
    draw.text((290, 105), "query front/back", fill=(90, 94, 98), font=font(26, True))
    draw.text((820, 105), "retrieved front/back", fill=(90, 94, 98), font=font(26, True))
    draw.text((1300, 105), "match", fill=(90, 94, 98), font=font(26, True))

    archive_cache: dict[str, zipfile.ZipFile] = {}

    def load(sample_id: str, category: str, suffix: str) -> Image.Image:
        archive_path = ARCHIVES / f"{category}.zip"
        if category not in archive_cache:
            archive_cache[category] = zipfile.ZipFile(archive_path)
        zf = archive_cache[category]
        prefix = f"{sample_id}/"
        name = next((item for item in zf.namelist() if item.startswith(prefix) and item.endswith(suffix)), None)
        if not name:
            return Image.new("RGB", (tile_w, tile_h), (245, 245, 245))
        img = Image.open(BytesIO(zf.read(name))).convert("RGB")
        img.thumbnail((tile_w, tile_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (tile_w, tile_h), "white")
        canvas.paste(img, ((tile_w - img.width) // 2, (tile_h - img.height) // 2))
        return canvas

    for i, row in enumerate(selected):
        y = 150 + i * 135
        qcat, rcat = row["query_category"], row["retrieved_category"]
        qid, rid = row["query_sample_id"], row["retrieved_sample_id"]
        draw.text((60, y + 70), short(qcat), fill=(30, 34, 38), font=font(25, True))
        image.paste(load(qid, qcat, "_camera_front.png"), (270, y))
        image.paste(load(qid, qcat, "_camera_back.png"), (465, y))
        image.paste(load(rid, rcat, "_camera_front.png"), (800, y))
        image.paste(load(rid, rcat, "_camera_back.png"), (995, y))
        color = (45, 140, 82) if qcat == rcat else (200, 72, 60)
        draw.rounded_rectangle((1290, y + 58, 1520, y + 122), radius=8, fill=color)
        draw.text((1315, y + 75), f"{short(rcat)} / r={row['rank_true_category']}", fill="white", font=font(24, True))
    for zf in archive_cache.values():
        zf.close()
    path = FIGURES / "fig_image_retrieval_examples.png"
    image.save(path, quality=95)
    return path


def write_report(results: list[dict], meta: list[dict]) -> None:
    missing_front = sum(1 for row in meta if row["has_front"] == "0" or row["has_front"] == 0)
    missing_back = sum(1 for row in meta if row["has_back"] == "0" or row["has_back"] == 0)
    lines = [
        "# Render Image Retrieval Baseline Report",
        "",
        "This experiment extracts deterministic image descriptors from front/back garment renders and evaluates nearest-neighbor retrieval on the same stratified split used by the structured-feature baselines.",
        "",
        "## Scope",
        "",
        f"- Samples with feature rows: {len(meta):,}",
        f"- Missing front renders: {missing_front}",
        f"- Missing back renders: {missing_back}",
        "",
        "## Results",
        "",
        "| Baseline | Features | Train | Test | Top-1 | Top-5 | MRR | Panel MAE | Stitch MAE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| `{row['baseline']}` | {row['features']} | {row['train_samples']} | {row['test_samples']} | "
            f"{row['top1']:.4f} | {row['top5']:.4f} | {row['mrr']:.4f} | {row['panel_mae']:.4f} | {row['stitch_mae']:.4f} |"
        )
    (EXP / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    EXP.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = read_csv(FULL_CSV)
    split_map = {row["sample_id"]: row["split"] for row in read_csv(SPLITS_CSV)}
    features, meta = build_features(rows)
    index = {row["sample_id"]: i for i, row in enumerate(meta)}
    train_meta = [row for row in meta if split_map[row["sample_id"]] == "train"]
    test_meta = [row for row in meta if split_map[row["sample_id"]] == "test"]
    train_idx = np.asarray([index[row["sample_id"]] for row in train_meta], dtype=np.int64)
    test_idx = np.asarray([index[row["sample_id"]] for row in test_meta], dtype=np.int64)

    front_dim = VIEW_FEATURE_DIM
    pair_dim = front_dim * 3
    results = [
        evaluate_nn(features[train_idx, :front_dim], features[test_idx, :front_dim], train_meta, test_meta, "nn_render_front"),
        evaluate_nn(features[train_idx, front_dim : front_dim * 2], features[test_idx, front_dim : front_dim * 2], train_meta, test_meta, "nn_render_back"),
        evaluate_nn(features[train_idx, :pair_dim], features[test_idx, :pair_dim], train_meta, test_meta, "nn_render_pair"),
    ]
    write_csv(EXP / "baseline_results.csv", results)
    baseline_chart(results)
    confusion_heatmap("nn_render_pair")
    make_qualitative_grid({row["sample_id"]: row for row in meta})
    write_report(results, meta)
    (EXP / "summary.json").write_text(
        json.dumps(
            {
                "features": int(features.shape[1]),
                "samples": len(meta),
                "train": len(train_meta),
                "test": len(test_meta),
                "best_top1": max(float(row["top1"]) for row in results),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    log(json.dumps({"samples": len(meta), "train": len(train_meta), "test": len(test_meta)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
