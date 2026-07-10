from __future__ import annotations

import argparse
import csv
import json
import math
import statistics as stats
import time
import zipfile
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "zenodo_3d_garments_sewing_patterns"
ARCHIVES = RAW / "archives"
EXP = ROOT / "experiments" / "exp02_full_quantitative_benchmarks"


def log(message: str) -> None:
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), message, flush=True)


def archive_category(path: Path) -> str:
    return path.name.removesuffix(".zip")


def sample_id_from_dir(dirname: str) -> str:
    return dirname.rstrip("/").split("/")[-1]


def mean(values: Iterable[float]) -> float:
    values = [v for v in values if v is not None and math.isfinite(v)]
    return float(stats.mean(values)) if values else 0.0


def median(values: Iterable[float]) -> float:
    values = sorted(v for v in values if v is not None and math.isfinite(v))
    return float(stats.median(values)) if values else 0.0


def q95(values: Iterable[float]) -> float:
    values = sorted(v for v in values if v is not None and math.isfinite(v))
    if not values:
        return 0.0
    index = min(len(values) - 1, math.ceil(0.95 * len(values)) - 1)
    return float(values[index])


def entropy(counter: Counter[str]) -> float:
    total = sum(counter.values())
    if total <= 0:
        return 0.0
    return float(-sum((n / total) * math.log2(n / total) for n in counter.values() if n > 0))


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def triangle_area(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    c: tuple[float, float, float],
) -> float:
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    return 0.5 * math.sqrt(cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2)


def parse_obj(raw: bytes) -> dict[str, float]:
    vertices: list[tuple[float, float, float]] = []
    faces: list[list[int]] = []
    duplicate_counter: Counter[tuple[int, int, int]] = Counter()

    for raw_line in raw.splitlines():
        if raw_line.startswith(b"v "):
            parts = raw_line.split()
            if len(parts) >= 4:
                try:
                    v = (float(parts[1]), float(parts[2]), float(parts[3]))
                except ValueError:
                    continue
                vertices.append(v)
                duplicate_counter[(round(v[0] * 100000), round(v[1] * 100000), round(v[2] * 100000))] += 1
        elif raw_line.startswith(b"f "):
            ids = []
            for token in raw_line.split()[1:]:
                try:
                    idx = int(token.split(b"/", 1)[0])
                except ValueError:
                    continue
                if idx < 0:
                    idx = len(vertices) + idx + 1
                ids.append(idx - 1)
            if len(ids) >= 3:
                faces.append(ids)

    edge_counter: Counter[tuple[int, int]] = Counter()
    adjacency: dict[int, set[int]] = defaultdict(set)
    edge_lengths: list[float] = []
    areas: list[float] = []
    aspect_ratios: list[float] = []
    degenerate_faces = 0

    for face in faces:
        valid = [idx for idx in face if 0 <= idx < len(vertices)]
        if len(valid) < 3:
            degenerate_faces += 1
            continue
        root = valid[0]
        for i in range(1, len(valid) - 1):
            tri = [root, valid[i], valid[i + 1]]
            a, b, c = (vertices[tri[0]], vertices[tri[1]], vertices[tri[2]])
            lengths = [distance(a, b), distance(b, c), distance(c, a)]
            area = triangle_area(a, b, c)
            areas.append(area)
            edge_lengths.extend(lengths)
            min_len = min(lengths)
            aspect_ratios.append(max(lengths) / min_len if min_len > 1e-12 else 0.0)
            if area <= 1e-10 or min_len <= 1e-12:
                degenerate_faces += 1
        for a, b in zip(valid, valid[1:] + valid[:1]):
            edge = (a, b) if a < b else (b, a)
            edge_counter[edge] += 1
            adjacency[a].add(b)
            adjacency[b].add(a)

    seen: set[int] = set()
    components = 0
    for start in adjacency:
        if start in seen:
            continue
        components += 1
        queue = deque([start])
        seen.add(start)
        while queue:
            node = queue.popleft()
            for nb in adjacency[node]:
                if nb not in seen:
                    seen.add(nb)
                    queue.append(nb)

    used_vertices = set(adjacency)
    boundary_edges = sum(1 for n in edge_counter.values() if n == 1)
    nonmanifold_edges = sum(1 for n in edge_counter.values() if n > 2)
    duplicate_vertices = sum(n - 1 for n in duplicate_counter.values() if n > 1)

    return {
        "vertices": len(vertices),
        "faces": len(faces),
        "used_vertices": len(used_vertices),
        "unused_vertices": max(0, len(vertices) - len(used_vertices)),
        "unique_edges": len(edge_counter),
        "boundary_edges": boundary_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "components": components,
        "duplicate_vertices": duplicate_vertices,
        "degenerate_faces": degenerate_faces,
        "mean_edge_length": mean(edge_lengths),
        "median_edge_length": median(edge_lengths),
        "q95_edge_length": q95(edge_lengths),
        "mean_triangle_area": mean(areas),
        "median_triangle_area": median(areas),
        "mean_aspect_ratio": mean(aspect_ratios),
        "q95_aspect_ratio": q95(aspect_ratios),
    }


def polygon_area(points: list[list[float]]) -> float:
    if len(points) < 3:
        return 0.0
    acc = 0.0
    for p, q in zip(points, points[1:] + points[:1]):
        acc += p[0] * q[1] - q[0] * p[1]
    return abs(acc) * 0.5


def polyline_length(points: list[list[float]]) -> float:
    if len(points) < 2:
        return 0.0
    total = 0.0
    for p, q in zip(points, points[1:] + points[:1]):
        total += math.hypot(p[0] - q[0], p[1] - q[1])
    return total


def parse_spec(raw: bytes) -> dict[str, float | str]:
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {
            "panel_count": 0,
            "pattern_edge_count": 0,
            "stitch_count": 0,
            "pattern_components": 0,
            "mean_panel_area": 0.0,
            "total_panel_area": 0.0,
            "mean_panel_perimeter": 0.0,
            "curved_edge_count": 0,
            "parameter_count": 0,
            "panel_names": "",
        }

    pattern = data.get("pattern", {}) if isinstance(data, dict) else {}
    panels = pattern.get("panels", {}) if isinstance(pattern, dict) else {}
    stitches = pattern.get("stitches", []) if isinstance(pattern, dict) else []
    parameters = data.get("parameters", {}) if isinstance(data, dict) else {}

    panel_names = list(panels.keys()) if isinstance(panels, dict) else []
    edge_count = 0
    curved_edge_count = 0
    areas = []
    perimeters = []
    for panel in panels.values() if isinstance(panels, dict) else []:
        edges = panel.get("edges", []) if isinstance(panel, dict) else []
        vertices = panel.get("vertices", []) if isinstance(panel, dict) else []
        edge_count += len(edges) if isinstance(edges, list) else 0
        if isinstance(edges, list):
            curved_edge_count += sum(1 for edge in edges if isinstance(edge, dict) and "curvature" in edge)
        if isinstance(vertices, list):
            pts = [p for p in vertices if isinstance(p, list) and len(p) >= 2]
            areas.append(polygon_area(pts))
            perimeters.append(polyline_length(pts))

    graph: dict[str, set[str]] = {name: set() for name in panel_names}
    valid_stitches = 0
    if isinstance(stitches, list):
        for stitch in stitches:
            stitch_panels = []
            if isinstance(stitch, list):
                for endpoint in stitch:
                    if isinstance(endpoint, dict):
                        panel = endpoint.get("panel")
                        if isinstance(panel, str):
                            stitch_panels.append(panel)
            if len(stitch_panels) >= 2:
                valid_stitches += 1
                for a in stitch_panels:
                    for b in stitch_panels:
                        if a != b and a in graph:
                            graph[a].add(b)

    seen: set[str] = set()
    components = 0
    for panel in graph:
        if panel in seen:
            continue
        components += 1
        queue = deque([panel])
        seen.add(panel)
        while queue:
            node = queue.popleft()
            for nb in graph[node]:
                if nb not in seen:
                    seen.add(nb)
                    queue.append(nb)

    return {
        "panel_count": len(panel_names),
        "pattern_edge_count": edge_count,
        "stitch_count": valid_stitches,
        "pattern_components": components,
        "mean_panel_area": mean(areas),
        "total_panel_area": sum(areas),
        "mean_panel_perimeter": mean(perimeters),
        "curved_edge_count": curved_edge_count,
        "parameter_count": len(parameters) if isinstance(parameters, dict) else 0,
        "panel_names": "|".join(panel_names),
    }


def parse_segmentation(raw: bytes) -> dict[str, float | str]:
    labels = [line.decode("utf-8", errors="replace").strip() for line in raw.splitlines()]
    labels = [label for label in labels if label]
    counter = Counter(labels)
    non_stitch = Counter({k: v for k, v in counter.items() if k.lower() != "stitch"})
    return {
        "seg_vertices": len(labels),
        "seg_label_count": len(counter),
        "seg_panel_label_count": len(non_stitch),
        "seg_stitch_fraction": counter.get("stitch", 0) / len(labels) if labels else 0.0,
        "seg_entropy": entropy(counter),
        "seg_panel_labels": "|".join(sorted(non_stitch)),
    }


def empty_obj(prefix: str) -> dict[str, float]:
    keys = [
        "vertices",
        "faces",
        "used_vertices",
        "unused_vertices",
        "unique_edges",
        "boundary_edges",
        "nonmanifold_edges",
        "components",
        "duplicate_vertices",
        "degenerate_faces",
        "mean_edge_length",
        "median_edge_length",
        "q95_edge_length",
        "mean_triangle_area",
        "median_triangle_area",
        "mean_aspect_ratio",
        "q95_aspect_ratio",
    ]
    return {f"{prefix}_{key}": 0 for key in keys}


def prefix_dict(prefix: str, values: dict[str, float]) -> dict[str, float]:
    return {f"{prefix}_{key}": value for key, value in values.items()}


def consistency_score(row: dict) -> float:
    checks = []
    checks.append(1.0 if row["panel_count"] > 0 else 0.0)
    checks.append(1.0 if row["stitch_count"] > 0 else 0.0)
    checks.append(1.0 if row["sim_vertices"] > 0 and row["sim_faces"] > 0 else 0.0)
    checks.append(1.0 if row["scan_vertices"] > 0 and row["scan_faces"] > 0 else 0.0)
    checks.append(1.0 if row["sim_nonmanifold_edges"] == 0 else 0.0)
    checks.append(1.0 if row["scan_nonmanifold_edges"] == 0 else 0.0)
    checks.append(1.0 if row["sim_seg_panel_label_count"] >= max(1, row["panel_count"]) else row["sim_seg_panel_label_count"] / max(1, row["panel_count"]))
    checks.append(1.0 if row["scan_seg_panel_label_count"] >= max(1, row["panel_count"]) else row["scan_seg_panel_label_count"] / max(1, row["panel_count"]))
    checks.append(1.0 if abs(row["sim_seg_vertices"] - row["sim_vertices"]) <= 1 else 0.0)
    checks.append(1.0 if abs(row["scan_seg_vertices"] - row["scan_vertices"]) <= 1 else 0.0)
    return round(100 * mean(checks), 6)


def audit_archive(path: Path, mesh_scope: str) -> list[dict]:
    category = archive_category(path)
    log(f"Opening {path.name}")
    rows: list[dict] = []
    with zipfile.ZipFile(path) as zf:
        groups: dict[str, list[str]] = defaultdict(list)
        for name in zf.namelist():
            if "/" not in name or name.endswith("/"):
                continue
            top = name.split("/", 1)[0]
            if top.startswith("__"):
                continue
            groups[top].append(name)

        total = len(groups)
        log(f"{path.name}: samples discovered = {total}")
        for index, (folder, names) in enumerate(sorted(groups.items()), start=1):
            if index % 100 == 0:
                log(f"{path.name}: quantitative audit {index}/{total}")
            name_set = set(names)
            sample_id = sample_id_from_dir(folder)
            spec_name = next((name for name in name_set if name.endswith("/specification.json")), None)
            sim_name = next((name for name in name_set if name.endswith("_sim.obj")), None)
            scan_name = next((name for name in name_set if name.endswith("_scan_imitation.obj")), None)
            sim_seg_name = next((name for name in name_set if name.endswith("_sim_segmentation.txt")), None)
            scan_seg_name = next((name for name in name_set if name.endswith("_scan_imitation_segmentation.txt")), None)

            row = {
                "category": category,
                "sample_id": sample_id,
                **(parse_spec(zf.read(spec_name)) if spec_name else {}),
                **empty_obj("sim"),
                **empty_obj("scan"),
                **(prefix_dict("sim", parse_segmentation(zf.read(sim_seg_name))) if sim_seg_name else {
                    "sim_seg_vertices": 0,
                    "sim_seg_label_count": 0,
                    "sim_seg_panel_label_count": 0,
                    "sim_seg_stitch_fraction": 0.0,
                    "sim_seg_entropy": 0.0,
                    "sim_seg_panel_labels": "",
                }),
                **(prefix_dict("scan", parse_segmentation(zf.read(scan_seg_name))) if scan_seg_name else {
                    "scan_seg_vertices": 0,
                    "scan_seg_label_count": 0,
                    "scan_seg_panel_label_count": 0,
                    "scan_seg_stitch_fraction": 0.0,
                    "scan_seg_entropy": 0.0,
                    "scan_seg_panel_labels": "",
                }),
            }
            if mesh_scope in {"sim", "both"} and sim_name:
                row.update(prefix_dict("sim", parse_obj(zf.read(sim_name))))
            if mesh_scope in {"scan", "both"} and scan_name:
                row.update(prefix_dict("scan", parse_obj(zf.read(scan_name))))
            row["pattern_mesh_consistency"] = consistency_score(row)
            rows.append(row)
    return rows


def summarize(rows: list[dict]) -> list[dict]:
    numeric_keys = [
        "panel_count",
        "pattern_edge_count",
        "stitch_count",
        "pattern_components",
        "mean_panel_area",
        "total_panel_area",
        "curved_edge_count",
        "parameter_count",
        "sim_vertices",
        "sim_faces",
        "sim_boundary_edges",
        "sim_nonmanifold_edges",
        "sim_components",
        "sim_degenerate_faces",
        "sim_mean_edge_length",
        "sim_mean_aspect_ratio",
        "sim_q95_aspect_ratio",
        "scan_vertices",
        "scan_faces",
        "scan_boundary_edges",
        "scan_nonmanifold_edges",
        "scan_components",
        "scan_degenerate_faces",
        "scan_mean_edge_length",
        "scan_mean_aspect_ratio",
        "scan_q95_aspect_ratio",
        "sim_seg_panel_label_count",
        "scan_seg_panel_label_count",
        "sim_seg_stitch_fraction",
        "scan_seg_stitch_fraction",
        "pattern_mesh_consistency",
    ]
    by_category: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_category[row["category"]].append(row)
    summary = []
    for category, items in sorted(by_category.items()):
        out = {"category": category, "samples": len(items)}
        for key in numeric_keys:
            out[f"mean_{key}"] = round(mean(float(row.get(key, 0) or 0) for row in items), 6)
            out[f"median_{key}"] = round(median(float(row.get(key, 0) or 0) for row in items), 6)
        summary.append(out)
    return summary


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh-scope", choices=["sim", "scan", "both"], default="both")
    parser.add_argument("--max-archives", type=int, default=0)
    args = parser.parse_args()

    EXP.mkdir(parents=True, exist_ok=True)
    archives = sorted(path for path in ARCHIVES.glob("*.zip") if path.name != "test.zip")
    if args.max_archives:
        archives = archives[: args.max_archives]
    if not archives:
        raise RuntimeError(f"No archives found in {ARCHIVES}")

    all_rows: list[dict] = []
    for archive in archives:
        rows = audit_archive(archive, args.mesh_scope)
        all_rows.extend(rows)
        out = EXP / f"{archive.stem}_quantitative.csv"
        write_csv(out, rows)
        log(f"Wrote {out}")

    full = EXP / "full_quantitative_benchmark.csv"
    write_csv(full, all_rows)
    category_rows = summarize(all_rows)
    write_csv(EXP / "category_quantitative_summary.csv", category_rows)
    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mesh_scope": args.mesh_scope,
        "samples": len(all_rows),
        "categories": len(category_rows),
        "mean_pattern_mesh_consistency": mean(float(row["pattern_mesh_consistency"]) for row in all_rows),
        "min_pattern_mesh_consistency": min(float(row["pattern_mesh_consistency"]) for row in all_rows) if all_rows else 0.0,
    }
    (EXP / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"Wrote {full}")
    log(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
