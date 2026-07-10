from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "exp02_full_quantitative_benchmarks"
FIGURES = EXP / "figures"
SUMMARY_CSV = EXP / "category_quantitative_summary.csv"
FULL_CSV = EXP / "full_quantitative_benchmark.csv"


def font(size: int, bold: bool = False):
    candidates = ("arialbd.ttf", "calibrib.ttf") if bold else ("arial.ttf", "calibri.ttf")
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def f(row: dict, key: str) -> float:
    try:
        return float(row.get(key, 0) or 0)
    except ValueError:
        return 0.0


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def short_name(name: str) -> str:
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
        "tee_sleeveless_1800": "tee-sl",
        "wb_dress_sleeveless_2600": "wb dress",
        "wb_pants_straight_1500": "wb pants",
    }.get(name, name)


def draw_bar_chart(
    rows: list[dict],
    path: Path,
    title: str,
    metrics: list[tuple[str, str, tuple[int, int, int]]],
    ylabel: str,
) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda row: f(row, metrics[0][0]))
    width, height = 2200, 1300
    margin_l, margin_r, margin_t, margin_b = 210, 90, 150, 230
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = font(48, True)
    label_font = font(30)
    small_font = font(25)
    draw.text((margin_l, 45), title, fill=(20, 24, 28), font=title_font)
    draw.text((42, margin_t + plot_h // 2 - 60), ylabel, fill=(70, 74, 78), font=label_font)
    draw.line((margin_l, margin_t, margin_l, margin_t + plot_h), fill=(30, 30, 30), width=3)
    draw.line((margin_l, margin_t + plot_h, margin_l + plot_w, margin_t + plot_h), fill=(30, 30, 30), width=3)
    max_v = max(max(f(row, key) for key, _, _ in metrics) for row in rows) * 1.12
    for tick in range(5):
        v = max_v * tick / 4
        y = margin_t + plot_h - int(plot_h * tick / 4)
        draw.line((margin_l - 8, y, margin_l + plot_w, y), fill=(226, 229, 232), width=1)
        draw.text((margin_l - 120, y - 15), f"{v:,.0f}", fill=(80, 84, 88), font=small_font)
    group_w = plot_w / len(rows)
    bar_w = min(50, group_w / (len(metrics) + 1))
    for i, row in enumerate(rows):
        x0 = margin_l + i * group_w + (group_w - len(metrics) * bar_w) / 2
        for j, (key, label, color) in enumerate(metrics):
            value = f(row, key)
            bh = int(plot_h * value / max_v) if max_v else 0
            x = int(x0 + j * bar_w)
            y = margin_t + plot_h - bh
            draw.rounded_rectangle((x, y, x + int(bar_w * 0.82), margin_t + plot_h), radius=4, fill=color)
        label = short_name(row["category"])
        tx = int(margin_l + i * group_w + group_w / 2)
        draw.text((tx - 42, margin_t + plot_h + 26), label, fill=(30, 34, 38), font=small_font)
        draw.text((tx - 30, margin_t + plot_h + 62), f"P{f(row, 'mean_panel_count'):.0f}/S{f(row, 'mean_stitch_count'):.0f}", fill=(100, 104, 108), font=small_font)
    lx = margin_l + plot_w - 520
    ly = 70
    for key, label, color in metrics:
        draw.rounded_rectangle((lx, ly, lx + 34, ly + 22), radius=4, fill=color)
        draw.text((lx + 46, ly - 6), label, fill=(50, 54, 58), font=label_font)
        ly += 42
    image.save(path, quality=95)
    return path


def draw_consistency_histogram(rows: list[dict], path: Path) -> Path:
    width, height = 1800, 1050
    margin_l, margin_r, margin_t, margin_b = 170, 80, 140, 170
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b
    bins = [(0, 70), (70, 80), (80, 90), (90, 99), (99, 100), (100, 100.0001)]
    labels = ["<70", "70-80", "80-90", "90-99", "99-<100", "100"]
    counts = [0] * len(bins)
    for row in rows:
        value = f(row, "pattern_mesh_consistency")
        for i, (lo, hi) in enumerate(bins):
            if lo <= value < hi:
                counts[i] += 1
                break
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((margin_l, 42), "Pattern-mesh consistency distribution", fill=(20, 24, 28), font=font(46, True))
    draw.line((margin_l, margin_t, margin_l, margin_t + plot_h), fill=(30, 30, 30), width=3)
    draw.line((margin_l, margin_t + plot_h, margin_l + plot_w, margin_t + plot_h), fill=(30, 30, 30), width=3)
    max_count = max(counts) * 1.08
    bar_w = plot_w / len(counts) * 0.65
    for i, count in enumerate(counts):
        cx = margin_l + (i + 0.5) * plot_w / len(counts)
        bh = int(plot_h * count / max_count) if max_count else 0
        x0 = int(cx - bar_w / 2)
        y0 = margin_t + plot_h - bh
        color = (44, 123, 182) if labels[i] == "100" else (215, 78, 56)
        draw.rounded_rectangle((x0, y0, int(x0 + bar_w), margin_t + plot_h), radius=8, fill=color)
        draw.text((int(cx - 54), margin_t + plot_h + 28), labels[i], fill=(30, 34, 38), font=font(28))
        draw.text((int(cx - 58), y0 - 42), f"{count:,}", fill=(30, 34, 38), font=font(28, True))
    image.save(path, quality=95)
    return path


def draw_skirt_ladder(rows: list[dict], path: Path) -> Path:
    rows = [row for row in rows if row["category"].startswith("skirt_")]
    rows = sorted(rows, key=lambda row: f(row, "mean_panel_count"))
    width, height = 1600, 980
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((70, 45), "Controlled skirt complexity ladder", fill=(20, 24, 28), font=font(44, True))
    colors = [(71, 139, 148), (232, 159, 66), (145, 92, 182)]
    max_faces = max(f(row, "mean_sim_faces") for row in rows) * 1.1
    card_w, card_h = 430, 650
    gap = 70
    top = 180
    for i, row in enumerate(rows):
        left = 70 + i * (card_w + gap)
        draw.rounded_rectangle((left, top, left + card_w, top + card_h), radius=18, outline=(205, 210, 215), width=3, fill=(252, 252, 252))
        color = colors[i % len(colors)]
        panels = int(f(row, "mean_panel_count"))
        stitches = int(f(row, "mean_stitch_count"))
        faces = f(row, "mean_sim_faces")
        boundary = f(row, "mean_sim_boundary_edges")
        draw.text((left + 30, top + 28), short_name(row["category"]), fill=(20, 24, 28), font=font(38, True))
        draw.text((left + 30, top + 90), f"{int(f(row, 'samples')):,} samples", fill=(90, 94, 98), font=font(26))
        cx, cy = left + card_w // 2, top + 260
        radius = 105
        for k in range(panels):
            angle0 = -90 + 360 * k / panels
            angle1 = -90 + 360 * (k + 0.84) / panels
            draw.pieslice((cx - radius, cy - radius, cx + radius, cy + radius), angle0, angle1, fill=color, outline="white", width=3)
        bar_top = top + 420
        bar_w = int((card_w - 60) * faces / max_faces)
        draw.text((left + 30, bar_top - 40), f"mean sim faces: {faces:,.0f}", fill=(40, 44, 48), font=font(27, True))
        draw.rounded_rectangle((left + 30, bar_top, left + 30 + bar_w, bar_top + 34), radius=8, fill=color)
        draw.text((left + 30, bar_top + 70), f"panels {panels}  stitches {stitches}", fill=(40, 44, 48), font=font(27))
        draw.text((left + 30, bar_top + 115), f"boundary edges {boundary:,.0f}", fill=(80, 84, 88), font=font(25))
    image.save(path, quality=95)
    return path


def write_report(summary_rows: list[dict], full_rows: list[dict]) -> Path:
    low = sorted(full_rows, key=lambda row: f(row, "pattern_mesh_consistency"))[:10]
    report = EXP / "REPORT.md"
    lines = [
        "# Full Quantitative Benchmark Report",
        "",
        "This experiment parses the full production subset directly from the Zenodo archives and computes pattern, mesh, segmentation, and pattern-mesh consistency metrics for both simulated and scan-imitation meshes.",
        "",
        "## Scope",
        "",
        f"- Samples: {len(full_rows):,}",
        f"- Categories: {len(summary_rows)}",
        f"- Mean pattern-mesh consistency: {sum(f(r, 'pattern_mesh_consistency') for r in full_rows) / len(full_rows):.4f}",
        "",
        "## Category Summary",
        "",
        "| Category | N | Panels | Stitches | Sim faces | Scan faces | Sim AR | Scan AR | Consistency |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| `{row['category']}` | {int(f(row, 'samples')):,} | {f(row, 'mean_panel_count'):.0f} | "
            f"{f(row, 'mean_stitch_count'):.0f} | {f(row, 'mean_sim_faces'):,.0f} | "
            f"{f(row, 'mean_scan_faces'):,.0f} | {f(row, 'mean_sim_mean_aspect_ratio'):.3f} | "
            f"{f(row, 'mean_scan_mean_aspect_ratio'):.3f} | {f(row, 'mean_pattern_mesh_consistency'):.3f} |"
        )
    lines += [
        "",
        "## Lowest-Consistency Samples",
        "",
        "| Category | Sample | Sim vertices | Scan vertices | Sim seg | Scan seg | Score |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in low:
        lines.append(
            f"| `{row['category']}` | `{row['sample_id']}` | {f(row, 'sim_vertices'):,.0f} | "
            f"{f(row, 'scan_vertices'):,.0f} | {f(row, 'sim_seg_vertices'):,.0f} | "
            f"{f(row, 'scan_seg_vertices'):,.0f} | {f(row, 'pattern_mesh_consistency'):.1f} |"
        )
    lines += [
        "",
        "## Generated Figures",
        "",
        "- `fig_mesh_quality_by_category.png`",
        "- `fig_pattern_structure_by_category.png`",
        "- `fig_consistency_histogram.png`",
        "- `fig_skirt_complexity_ladder.png`",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")
    return report


def main() -> int:
    summary_rows = read_csv(SUMMARY_CSV)
    full_rows = read_csv(FULL_CSV)
    draw_bar_chart(
        summary_rows,
        FIGURES / "fig_mesh_quality_by_category.png",
        "Mesh quality and resolution by garment category",
        [
            ("mean_sim_faces", "sim faces", (44, 123, 182)),
            ("mean_scan_faces", "scan faces", (247, 147, 30)),
            ("mean_sim_boundary_edges", "sim boundary edges", (93, 164, 101)),
        ],
        "count",
    )
    draw_bar_chart(
        summary_rows,
        FIGURES / "fig_pattern_structure_by_category.png",
        "Pattern structure by garment category",
        [
            ("mean_panel_count", "panels", (44, 123, 182)),
            ("mean_stitch_count", "stitches", (247, 147, 30)),
            ("mean_curved_edge_count", "curved edges", (93, 164, 101)),
        ],
        "count",
    )
    draw_consistency_histogram(full_rows, FIGURES / "fig_consistency_histogram.png")
    draw_skirt_ladder(summary_rows, FIGURES / "fig_skirt_complexity_ladder.png")
    report = write_report(summary_rows, full_rows)
    print(f"Wrote {report}")
    print(f"Wrote figures to {FIGURES}")
    print(json.dumps({"samples": len(full_rows), "categories": len(summary_rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
