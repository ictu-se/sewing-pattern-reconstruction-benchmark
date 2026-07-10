from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics as stats
import time
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "zenodo_3d_garments_sewing_patterns"
ARCHIVES = RAW / "archives"
EXP = ROOT / "experiments" / "exp01_zenodo_full_pattern_audit"
REQUIRED_SUFFIXES = [
    "_camera_front.png",
    "_camera_back.png",
    "_pattern.png",
    "_pattern.svg",
    "_sim.obj",
    "_scan_imitation.obj",
    "_sim_segmentation.txt",
    "_scan_imitation_segmentation.txt",
    "specification.json",
]


def log(message: str) -> None:
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), message, flush=True)


def archive_category(path: Path) -> str:
    return path.name.removesuffix(".zip")


def svg_path_count(text: str) -> int:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return 0
    count = 0
    for elem in root.iter():
        if elem.tag.lower().endswith("path"):
            count += 1
    return count


def walk_spec(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk_spec(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_spec(value)


def spec_counts(text: str) -> tuple[int, int, int]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return 0, 0, 0
    panels = edges = stitches = 0
    for node in walk_spec(data):
        if "panels" in node and isinstance(node["panels"], dict):
            panels = max(panels, len(node["panels"]))
        if "pattern" in node and isinstance(node["pattern"], dict):
            maybe_panels = node["pattern"].get("panels")
            if isinstance(maybe_panels, dict):
                panels = max(panels, len(maybe_panels))
        for key in ("stitches", "stitching_rules", "stitch_rules"):
            value = node.get(key)
            if isinstance(value, list):
                stitches = max(stitches, len(value))
        for key in ("edges", "edge_loop", "edge_sequence"):
            value = node.get(key)
            if isinstance(value, list):
                edges += len(value)
    return panels, edges, stitches


def obj_counts(raw: bytes) -> tuple[int, int, int]:
    vertices = faces = lines = 0
    for line in raw.splitlines():
        if line.startswith(b"v "):
            vertices += 1
        elif line.startswith(b"f "):
            faces += 1
        elif line.startswith(b"l "):
            lines += 1
    return vertices, faces, lines


def sample_id_from_dir(dirname: str) -> str:
    return dirname.rstrip("/").split("/")[-1]


def audit_archive(path: Path, include_mesh_counts: bool) -> list[dict]:
    category = archive_category(path)
    log(f"Opening {path.name}")
    with zipfile.ZipFile(path) as zf:
        groups: dict[str, list[str]] = defaultdict(list)
        for name in zf.namelist():
            if "/" not in name or name.endswith("/"):
                continue
            top = name.split("/", 1)[0]
            if top.startswith("__") or top.endswith(".txt") or top.endswith(".json"):
                continue
            groups[top].append(name)
        rows = []
        total = len(groups)
        log(f"{path.name}: samples discovered = {total}")
        for index, (folder, names) in enumerate(sorted(groups.items()), start=1):
            if index % 250 == 0:
                log(f"{path.name}: audited {index}/{total}")
            name_set = set(names)
            basenames = {Path(name).name for name in names}
            sample_id = sample_id_from_dir(folder)
            has = {suffix: any(base.endswith(suffix) for base in basenames) for suffix in REQUIRED_SUFFIXES}
            spec_name = next((name for name in name_set if name.endswith("/specification.json")), None)
            svg_name = next((name for name in name_set if name.endswith("_pattern.svg")), None)
            sim_name = next((name for name in name_set if name.endswith("_sim.obj")), None)
            scan_name = next((name for name in name_set if name.endswith("_scan_imitation.obj")), None)
            panels = pattern_edges = stitches = svg_paths = 0
            if spec_name:
                panels, pattern_edges, stitches = spec_counts(zf.read(spec_name).decode("utf-8", errors="replace"))
            if svg_name:
                svg_paths = svg_path_count(zf.read(svg_name).decode("utf-8", errors="replace"))
            sim_v = sim_f = sim_l = scan_v = scan_f = scan_l = 0
            if include_mesh_counts and sim_name:
                sim_v, sim_f, sim_l = obj_counts(zf.read(sim_name))
            if include_mesh_counts and scan_name:
                scan_v, scan_f, scan_l = obj_counts(zf.read(scan_name))
            present = sum(1 for value in has.values() if value)
            rows.append(
                {
                    "category": category,
                    "sample_id": sample_id,
                    "completeness": round(100 * present / len(REQUIRED_SUFFIXES), 6),
                    "has_front": int(has["_camera_front.png"]),
                    "has_back": int(has["_camera_back.png"]),
                    "has_pattern_png": int(has["_pattern.png"]),
                    "has_pattern_svg": int(has["_pattern.svg"]),
                    "has_sim_obj": int(has["_sim.obj"]),
                    "has_scan_obj": int(has["_scan_imitation.obj"]),
                    "has_sim_seg": int(has["_sim_segmentation.txt"]),
                    "has_scan_seg": int(has["_scan_imitation_segmentation.txt"]),
                    "has_spec": int(has["specification.json"]),
                    "panel_count": panels,
                    "pattern_edge_count": pattern_edges,
                    "stitch_count": stitches,
                    "svg_path_count": svg_paths,
                    "sim_vertices": sim_v,
                    "sim_faces": sim_f,
                    "sim_lines": sim_l,
                    "scan_vertices": scan_v,
                    "scan_faces": scan_f,
                    "scan_lines": scan_l,
                }
            )
    return rows


def mean(values: list[float]) -> float:
    return float(stats.mean(values)) if values else 0.0


def summarize(rows: list[dict]) -> dict:
    by_category: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_category[row["category"]].append(row)
    categories = {}
    for category, items in sorted(by_category.items()):
        categories[category] = {
            "samples": len(items),
            "avg_completeness": mean([float(row["completeness"]) for row in items]),
            "avg_panels": mean([float(row["panel_count"]) for row in items]),
            "avg_pattern_edges": mean([float(row["pattern_edge_count"]) for row in items]),
            "avg_stitches": mean([float(row["stitch_count"]) for row in items]),
            "avg_svg_paths": mean([float(row["svg_path_count"]) for row in items]),
            "avg_sim_vertices": mean([float(row["sim_vertices"]) for row in items if int(row["sim_vertices"]) > 0]),
            "avg_sim_faces": mean([float(row["sim_faces"]) for row in items if int(row["sim_faces"]) > 0]),
        }
    return {
        "total_samples": len(rows),
        "categories": categories,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-mesh-counts", action="store_true", help="Fast metadata-only audit.")
    parser.add_argument("--max-archives", type=int, default=0, help="Debug limit. 0 means all archives.")
    args = parser.parse_args()

    EXP.mkdir(parents=True, exist_ok=True)
    archives = sorted(ARCHIVES.glob("*.zip"))
    if args.max_archives:
        archives = archives[: args.max_archives]
    if not archives:
        raise RuntimeError(f"No archives found in {ARCHIVES}")
    all_rows = []
    for archive in archives:
        rows = audit_archive(archive, include_mesh_counts=not args.skip_mesh_counts)
        all_rows.extend(rows)
        part_path = EXP / f"{archive.stem}_audit.csv"
        with part_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        log(f"Wrote {part_path}")

    out_csv = EXP / "zenodo_full_pattern_audit.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)
    summary = summarize(all_rows)
    (EXP / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log(f"Wrote {out_csv}")
    log(f"Total samples audited: {summary['total_samples']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
