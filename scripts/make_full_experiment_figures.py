from __future__ import annotations

import csv
import math
import zipfile
from collections import defaultdict
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "exp01_zenodo_full_pattern_audit"
ARCHIVES = ROOT / "raw" / "zenodo_3d_garments_sewing_patterns" / "archives"
FIGURES = EXP / "figures"
CSV_PATH = EXP / "zenodo_full_pattern_audit.csv"


def font(size: int, bold: bool = False):
    candidates = ("arialbd.ttf", "calibrib.ttf") if bold else ("arial.ttf", "calibri.ttf")
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def fit_box(image: Image.Image, width: int, height: int) -> Image.Image:
    image = image.convert("RGB")
    image.thumbnail((width, height), Image.LANCZOS)
    return image


def paste_center(canvas: Image.Image, image: Image.Image, box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    x = left + (right - left - image.width) // 2
    y = top + (bottom - top - image.height) // 2
    canvas.paste(image, (x, y))


def read_rows() -> list[dict]:
    with CSV_PATH.open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def representative_rows(rows: list[dict], count: int = 4) -> list[dict]:
    rows = [row for row in rows if row["completeness"] == "100.0" and float(row["sim_faces"]) > 0]
    rows.sort(key=lambda row: float(row["sim_faces"]))
    if len(rows) <= count:
        return rows
    indices = [round(i * (len(rows) - 1) / (count - 1)) for i in range(count)]
    return [rows[index] for index in indices]


def image_from_zip(zf: zipfile.ZipFile, sample_id: str, suffix: str) -> Image.Image:
    prefix = f"{sample_id}/"
    name = next(
        item for item in zf.namelist() if item.startswith(prefix) and item.endswith(suffix)
    )
    return Image.open(BytesIO(zf.read(name))).convert("RGB")


def make_evidence_sheet(rows: list[dict]) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    by_category: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["category"] != "test":
            by_category[row["category"]].append(row)

    categories = sorted(by_category)
    tile_w, tile_h = 238, 104
    label_w = 330
    header_h = 52
    row_h = tile_h + 18
    width = label_w + 4 * tile_w + 40
    height = header_h + len(categories) * row_h + 24
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 14), "Full-data representative render-pattern evidence by category", fill=(20, 22, 24), font=font(24, True))

    y = header_h
    for category in categories:
        draw.text((18, y + 35), category.replace("_", " "), fill=(20, 22, 24), font=font(17, True))
        archive = ARCHIVES / f"{category}.zip"
        with zipfile.ZipFile(archive) as zf:
            reps = representative_rows(by_category[category], count=4)
            for col, row in enumerate(reps):
                x = label_w + col * tile_w
                sample_id = row["sample_id"]
                front = fit_box(image_from_zip(zf, sample_id, "_camera_front.png"), 82, 96)
                pattern = fit_box(image_from_zip(zf, sample_id, "_pattern.png"), 132, 82)
                tile = Image.new("RGB", (tile_w, tile_h), "white")
                paste_center(tile, front, (0, 4, 86, 100))
                paste_center(tile, pattern, (92, 10, 232, 94))
                sheet.paste(tile, (x, y))
        y += row_h
    out = FIGURES / "fig_full_category_render_pattern_evidence.png"
    sheet.save(out, quality=95)
    return out


def make_complexity_chart(rows: list[dict]) -> Path:
    by_category: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["category"] != "test":
            by_category[row["category"]].append(row)

    summary = []
    for category, items in by_category.items():
        summary.append(
            {
                "category": category.replace("_", " "),
                "faces": sum(float(row["sim_faces"]) for row in items) / len(items),
                "panels": sum(float(row["panel_count"]) for row in items) / len(items),
                "stitches": sum(float(row["stitch_count"]) for row in items) / len(items),
            }
        )
    summary.sort(key=lambda row: row["faces"])

    width, height = 2600, 920
    left, top, bottom = 280, 80, 780
    plot_w = width - left - 80
    plot_h = bottom - top
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((40, 24), "Full-data garment category complexity", fill=(20, 22, 24), font=font(30, True))
    max_faces = max(row["faces"] for row in summary)
    bar_h = plot_h / len(summary) * 0.58
    for idx, row in enumerate(summary):
        y = top + idx * (plot_h / len(summary)) + 6
        x1 = left + int(plot_w * row["faces"] / max_faces)
        draw.rectangle((left, y, x1, y + bar_h), fill=(126, 166, 210))
        draw.text((22, y + 2), row["category"], fill=(20, 22, 24), font=font(16))
        label = f"{row['faces']:.0f} faces | {row['panels']:.0f} panels | {row['stitches']:.0f} stitches"
        label_x = min(x1 + 10, width - 520)
        draw.text((label_x, y + 2), label, fill=(20, 22, 24), font=font(15))
    draw.line((left, top - 8, left, bottom + 8), fill=(80, 80, 80), width=2)
    draw.text((left, bottom + 32), "Mean simulated mesh faces; labels also show mean panel and stitch counts.", fill=(70, 70, 70), font=font(18))
    out = FIGURES / "fig_full_category_complexity_chart.png"
    canvas.save(out, quality=95)
    return out


def main() -> int:
    rows = read_rows()
    print(make_evidence_sheet(rows))
    print(make_complexity_chart(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
