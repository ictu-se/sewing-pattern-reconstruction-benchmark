from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "exp03_retrieval_reconstruction_baselines"
FIGURES = EXP / "figures"


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


def per_category_accuracy(feature_set: str) -> list[dict]:
    rows = read_csv(EXP / f"confusion_{feature_set}.csv")
    totals = defaultdict(int)
    correct = defaultdict(int)
    for row in rows:
        true = row["true_category"]
        pred = row["pred_category"]
        count = int(row["count"])
        totals[true] += count
        if true == pred:
            correct[true] += count
    return [
        {
            "feature_set": feature_set,
            "category": category,
            "test_samples": totals[category],
            "top1": correct[category] / totals[category] if totals[category] else 0.0,
        }
        for category in sorted(totals)
    ]


def heatmap(feature_set: str) -> Path:
    rows = read_csv(EXP / f"confusion_{feature_set}.csv")
    categories = sorted({row["true_category"] for row in rows} | {row["pred_category"] for row in rows})
    index = {cat: i for i, cat in enumerate(categories)}
    matrix = [[0 for _ in categories] for _ in categories]
    for row in rows:
        matrix[index[row["true_category"]]][index[row["pred_category"]]] += int(row["count"])
    row_sums = [sum(row) or 1 for row in matrix]

    cell = 72
    left = 310
    top = 170
    width = left + cell * len(categories) + 80
    height = top + cell * len(categories) + 230
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((left, 45), f"Confusion heatmap: {feature_set}", fill=(20, 24, 28), font=font(44, True))
    for i, true in enumerate(categories):
        draw.text((34, top + i * cell + 20), short(true), fill=(35, 39, 43), font=font(24))
        draw.text((left + i * cell + 6, top + cell * len(categories) + 22), short(true), fill=(35, 39, 43), font=font(22))
    draw.text((34, top - 54), "true", fill=(90, 94, 98), font=font(28, True))
    draw.text((left, top + cell * len(categories) + 90), "predicted", fill=(90, 94, 98), font=font(28, True))
    for r in range(len(categories)):
        for c in range(len(categories)):
            v = matrix[r][c] / row_sums[r]
            blue = int(245 - 180 * v)
            color = (blue, blue + 5 if blue < 245 else blue, 255)
            x0 = left + c * cell
            y0 = top + r * cell
            draw.rectangle((x0, y0, x0 + cell - 2, y0 + cell - 2), fill=color)
            if v >= 0.08:
                draw.text((x0 + 13, y0 + 23), f"{v:.2f}", fill=(20, 24, 28), font=font(20, True))
    path = FIGURES / f"fig_confusion_{feature_set}.png"
    image.save(path, quality=95)
    return path


def main() -> int:
    all_rows = []
    for feature_set in ("pattern", "mesh", "segmentation", "combined"):
        all_rows.extend(per_category_accuracy(feature_set))
        heatmap(feature_set)
    write_csv(EXP / "per_category_top1.csv", all_rows)
    print(f"Wrote diagnostics to {EXP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
