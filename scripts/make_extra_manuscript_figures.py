from __future__ import annotations

import csv
import zipfile
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ARCHIVES = ROOT / "raw" / "zenodo_3d_garments_sewing_patterns" / "archives"
EXP02 = ROOT / "experiments" / "exp02_full_quantitative_benchmarks"
EXP03 = ROOT / "experiments" / "exp03_retrieval_reconstruction_baselines"
EXP04 = ROOT / "experiments" / "exp04_render_image_retrieval_baselines"
FIGURES = ROOT / "experiments" / "exp05_manuscript_extra_figures" / "figures"


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
        "wb_dress_sleeveless_2600": "wb-dress",
        "wb_pants_straight_1500": "wb-pants",
    }.get(name, name)


def load_render(cache: dict[str, zipfile.ZipFile], category: str, sample_id: str, suffix: str, size: tuple[int, int]) -> Image.Image:
    if category not in cache:
        cache[category] = zipfile.ZipFile(ARCHIVES / f"{category}.zip")
    zf = cache[category]
    prefix = f"{sample_id}/"
    name = next((item for item in zf.namelist() if item.startswith(prefix) and item.endswith(suffix)), None)
    canvas = Image.new("RGB", size, "white")
    if not name:
        return canvas
    img = Image.open(BytesIO(zf.read(name))).convert("RGB")
    img.thumbnail(size, Image.Resampling.LANCZOS)
    canvas.paste(img, ((size[0] - img.width) // 2, (size[1] - img.height) // 2))
    return canvas


def render_error_gallery() -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = [row for row in read_csv(EXP04 / "retrieval_examples_nn_render_pair.csv") if row.get("is_error") == "1"]
    rows = rows[:10]
    width, height = 1900, 1500
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((60, 38), "Render retrieval error gallery", fill=(20, 24, 28), font=font(44, True))
    draw.text((400, 105), "query", fill=(90, 94, 98), font=font(28, True))
    draw.text((900, 105), "retrieved", fill=(90, 94, 98), font=font(28, True))
    draw.text((1370, 105), "diagnosis", fill=(90, 94, 98), font=font(28, True))
    tile = (160, 160)
    row_h = 128
    top = 155
    cache: dict[str, zipfile.ZipFile] = {}
    try:
        for i, row in enumerate(rows):
            y = top + i * row_h
            qcat, rcat = row["query_category"], row["retrieved_category"]
            qid, rid = row["query_sample_id"], row["retrieved_sample_id"]
            draw.text((60, y + 45), f"{short(qcat)} -> {short(rcat)}", fill=(30, 34, 38), font=font(24, True))
            image.paste(load_render(cache, qcat, qid, "_camera_front.png", tile), (365, y))
            image.paste(load_render(cache, qcat, qid, "_camera_back.png", tile), (530, y))
            image.paste(load_render(cache, rcat, rid, "_camera_front.png", tile), (875, y))
            image.paste(load_render(cache, rcat, rid, "_camera_back.png", tile), (1040, y))
            diagnosis = "upper-body silhouette" if "jacket" in qcat or "tee" in qcat else "lower-body/template similarity"
            if "wb" in qcat or "wb" in rcat:
                diagnosis = "waistband variant ambiguity"
            if "jumpsuit" in qcat or "dress" in qcat:
                diagnosis = "full-body silhouette ambiguity"
            draw.text((1360, y + 52), diagnosis, fill=(55, 59, 63), font=font(24))
            draw.text((1360, y + 84), f"true rank {row['rank_true_category']}", fill=(90, 94, 98), font=font(22))
    finally:
        for zf in cache.values():
            zf.close()
    path = FIGURES / "fig_render_error_gallery.png"
    image.save(path, quality=95)
    return path


def traditional_gap_map() -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = [
        ("Long tunic panels", "dress / wb dress", "partial", "need side-slit and length annotations"),
        ("Side slits", "none", "missing", "explicit opening and seam labels"),
        ("Standing collar", "jacket / hood", "partial", "collar pattern and neckline rules"),
        ("Set-in or raglan sleeves", "tee / jacket", "partial", "sleeve construction variants"),
        ("Layered trousers", "pants / wb pants", "partial", "paired garment outfit relation"),
        ("Motif alignment", "none", "missing", "texture and seam-aware motif annotations"),
        ("Fabric drape realism", "all synthetic meshes", "partial", "material and simulation metadata"),
        ("Cultural style labels", "none", "missing", "expert-validated cultural taxonomy"),
    ]
    width, height = 1800, 1120
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((60, 40), "Traditional garment transfer gap map", fill=(20, 24, 28), font=font(44, True))
    headers = ["Requirement", "Dataset proxy", "Coverage", "Needed extension"]
    xs = [70, 520, 880, 1120]
    y = 140
    for x, header in zip(xs, headers):
        draw.text((x, y), header, fill=(70, 74, 78), font=font(26, True))
    y += 55
    colors = {"partial": (238, 170, 62), "missing": (204, 83, 72)}
    for req, proxy, coverage, need in rows:
        draw.line((60, y - 12, width - 60, y - 12), fill=(226, 229, 232), width=2)
        draw.text((xs[0], y), req, fill=(25, 29, 33), font=font(25, True))
        draw.text((xs[1], y), proxy, fill=(45, 49, 53), font=font(24))
        color = colors[coverage]
        draw.rounded_rectangle((xs[2], y - 4, xs[2] + 150, y + 38), radius=8, fill=color)
        draw.text((xs[2] + 20, y + 5), coverage, fill="white", font=font(22, True))
        draw.text((xs[3], y), need, fill=(45, 49, 53), font=font(24))
        y += 95
    draw.line((60, y - 12, width - 60, y - 12), fill=(226, 229, 232), width=2)
    path = FIGURES / "fig_traditional_gap_map.png"
    image.save(path, quality=95)
    return path


def pipeline_overview() -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    width, height = 1800, 1050
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((70, 45), "Full-data benchmark pipeline", fill=(20, 24, 28), font=font(44, True))
    steps = [
        ("Zenodo archives", "14 verified files\n84.77 GB compressed"),
        ("Evidence audit", "22,457 samples\n9 required evidence items"),
        ("Quantitative parse", "22,450 production samples\npattern + mesh + segmentation"),
        ("Consistency gate", "22,448 perfect samples\n2 low-score cases"),
        ("Retrieval baselines", "structured features\nrender image descriptors"),
        ("Transfer analysis", "traditional-garment gaps\nfuture dataset schema"),
    ]
    x0, y0 = 90, 190
    box_w, box_h = 250, 210
    gap = 45
    colors = [(44, 123, 182), (93, 164, 101), (247, 147, 30), (145, 92, 182), (74, 154, 189), (206, 96, 72)]
    for i, (title, body) in enumerate(steps):
        x = x0 + i * (box_w + gap)
        draw.rounded_rectangle((x, y0, x + box_w, y0 + box_h), radius=16, fill=(248, 249, 250), outline=(205, 210, 215), width=3)
        draw.rounded_rectangle((x, y0, x + box_w, y0 + 54), radius=16, fill=colors[i])
        draw.text((x + 18, y0 + 14), title, fill="white", font=font(23, True))
        yy = y0 + 82
        for line in body.split("\n"):
            draw.text((x + 18, yy), line, fill=(35, 39, 43), font=font(22))
            yy += 34
        if i < len(steps) - 1:
            ax = x + box_w + 8
            ay = y0 + box_h // 2
            draw.line((ax, ay, ax + gap - 18, ay), fill=(80, 84, 88), width=4)
            draw.polygon([(ax + gap - 18, ay - 10), (ax + gap - 18, ay + 10), (ax + gap - 2, ay)], fill=(80, 84, 88))
    draw.text((90, 520), "Outputs", fill=(20, 24, 28), font=font(36, True))
    outputs = [
        "evidence CSVs",
        "mesh-quality metrics",
        "pattern graph metrics",
        "consistency score",
        "splits and baselines",
        "figures and manuscript tables",
    ]
    for i, item in enumerate(outputs):
        x = 120 + (i % 3) * 520
        y = 590 + (i // 3) * 110
        draw.rounded_rectangle((x, y, x + 420, y + 64), radius=10, fill=(245, 247, 249), outline=(210, 215, 220))
        draw.text((x + 24, y + 17), item, fill=(45, 49, 53), font=font(25, True))
    path = FIGURES / "fig_benchmark_pipeline.png"
    image.save(path, quality=95)
    return path


def modality_comparison() -> Path:
    struct_rows = read_csv(EXP03 / "baseline_results.csv")
    render_rows = read_csv(EXP04 / "baseline_results.csv")
    rows = [
        ("random", float(next(r for r in struct_rows if r["baseline"] == "random_category")["top1"])),
        ("mesh", float(next(r for r in struct_rows if r["baseline"] == "nn_mesh")["top1"])),
        ("segmentation", float(next(r for r in struct_rows if r["baseline"] == "nn_segmentation")["top1"])),
        ("render front", float(next(r for r in render_rows if r["baseline"] == "nn_render_front")["top1"])),
        ("render pair", float(next(r for r in render_rows if r["baseline"] == "nn_render_pair")["top1"])),
        ("pattern", float(next(r for r in struct_rows if r["baseline"] == "nn_pattern")["top1"])),
        ("combined", float(next(r for r in struct_rows if r["baseline"] == "nn_combined")["top1"])),
    ]
    width, height = 1600, 980
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((70, 42), "Modality ablation: top-1 retrieval accuracy", fill=(20, 24, 28), font=font(42, True))
    left, top, plot_w, plot_h = 230, 150, 1250, 640
    draw.line((left, top, left, top + plot_h), fill=(30, 30, 30), width=3)
    draw.line((left, top + plot_h, left + plot_w, top + plot_h), fill=(30, 30, 30), width=3)
    for t in range(6):
        y = top + plot_h - int(plot_h * t / 5)
        draw.line((left - 8, y, left + plot_w, y), fill=(226, 229, 232), width=1)
        draw.text((left - 80, y - 14), f"{t/5:.1f}", fill=(80, 84, 88), font=font(24))
    group_w = plot_w / len(rows)
    for i, (name, value) in enumerate(rows):
        x = left + i * group_w + group_w * 0.2
        h = int(plot_h * value)
        color = (44, 123, 182) if value < 0.95 else (93, 164, 101)
        draw.rounded_rectangle((int(x), top + plot_h - h, int(x + group_w * 0.55), top + plot_h), radius=7, fill=color)
        draw.text((int(x - 8), top + plot_h - h - 34), f"{value:.3f}", fill=(35, 39, 43), font=font(22, True))
        draw.text((int(left + i * group_w + 8), top + plot_h + 28), name, fill=(35, 39, 43), font=font(22))
    path = FIGURES / "fig_modality_ablation.png"
    image.save(path, quality=95)
    return path


def consistency_components() -> Path:
    width, height = 1700, 980
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((70, 42), "Pattern-mesh consistency score components", fill=(20, 24, 28), font=font(42, True))
    components = [
        ("pattern panels", "P > 0"),
        ("stitch rules", "S > 0"),
        ("sim mesh", "Vsim,Fsim > 0"),
        ("scan mesh", "Vscan,Fscan > 0"),
        ("sim manifold", "nonmanifold = 0"),
        ("scan manifold", "nonmanifold = 0"),
        ("sim labels", "Lsim >= P"),
        ("scan labels", "Lscan >= P"),
        ("sim seg length", "|seg - V| <= 1"),
        ("scan seg length", "|seg - V| <= 1"),
    ]
    cols = 5
    box_w, box_h = 290, 150
    x0, y0 = 95, 170
    for i, (name, rule) in enumerate(components):
        x = x0 + (i % cols) * (box_w + 28)
        y = y0 + (i // cols) * (box_h + 80)
        draw.rounded_rectangle((x, y, x + box_w, y + box_h), radius=15, fill=(248, 249, 250), outline=(205, 210, 215), width=3)
        draw.text((x + 20, y + 24), name, fill=(25, 29, 33), font=font(25, True))
        draw.text((x + 20, y + 76), rule, fill=(65, 69, 73), font=font(24))
    draw.rounded_rectangle((410, 700, 1290, 800), radius=18, fill=(44, 123, 182))
    draw.text((455, 730), "Q = 100 x mean(component checks)", fill="white", font=font(34, True))
    path = FIGURES / "fig_consistency_components.png"
    image.save(path, quality=95)
    return path


def traditional_schema_flow() -> Path:
    width, height = 1700, 980
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((70, 42), "Traditional-garment dataset schema", fill=(20, 24, 28), font=font(42, True))
    items = [
        ("Visual", "front/back/detail\ncamera metadata"),
        ("Pattern", "panels, slits\ncollars, sleeves"),
        ("Stitch", "seam pairs\nopen boundaries"),
        ("Mesh", "sim + scan\nsegmentation"),
        ("Material", "fabric, drape\nsimulation params"),
        ("Motif", "texture rules\nseam alignment"),
        ("Culture", "style labels\nexpert validation"),
        ("Splits", "category + style\ncross-style tests"),
    ]
    x0, y0 = 100, 180
    box_w, box_h = 330, 145
    for i, (title, body) in enumerate(items):
        x = x0 + (i % 4) * 390
        y = y0 + (i // 4) * 245
        draw.rounded_rectangle((x, y, x + box_w, y + box_h), radius=16, fill=(248, 249, 250), outline=(205, 210, 215), width=3)
        draw.text((x + 22, y + 18), title, fill=(25, 29, 33), font=font(28, True))
        yy = y + 65
        for line in body.split("\n"):
            draw.text((x + 22, yy), line, fill=(70, 74, 78), font=font(22))
            yy += 30
    draw.text((120, 760), "Minimum requirement: every sample should preserve the same tuple (I, P, S, M, A), plus material, motif, and cultural validation metadata.", fill=(45, 49, 53), font=font(26))
    path = FIGURES / "fig_traditional_schema_flow.png"
    image.save(path, quality=95)
    return path


def main() -> int:
    print(render_error_gallery())
    print(traditional_gap_map())
    print(pipeline_overview())
    print(modality_comparison())
    print(consistency_components())
    print(traditional_schema_flow())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
