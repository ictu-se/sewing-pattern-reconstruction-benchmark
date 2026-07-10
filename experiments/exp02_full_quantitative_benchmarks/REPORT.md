# Full Quantitative Benchmark Report

This experiment parses the full production subset directly from the Zenodo archives and computes pattern, mesh, segmentation, and pattern-mesh consistency metrics for both simulated and scan-imitation meshes.

## Scope

- Samples: 22,450
- Categories: 12
- Mean pattern-mesh consistency: 99.9964

## Category Summary

| Category | N | Panels | Stitches | Sim faces | Scan faces | Sim AR | Scan AR | Consistency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `dress_sleeveless_2550` | 2,550 | 4 | 10 | 17,887 | 17,309 | 1.341 | 1.341 | 99.984 |
| `jacket_2200` | 2,200 | 7 | 12 | 35,060 | 33,955 | 1.334 | 1.334 | 100.000 |
| `jacket_hood_2700` | 2,700 | 9 | 18 | 37,743 | 35,685 | 1.336 | 1.334 | 100.000 |
| `jumpsuit_sleeveless_2000` | 2,000 | 6 | 14 | 16,673 | 16,072 | 1.363 | 1.361 | 99.980 |
| `pants_straight_sides_1000` | 1,000 | 4 | 6 | 11,992 | 11,134 | 1.388 | 1.385 | 100.000 |
| `skirt_2_panels_1200` | 1,200 | 2 | 4 | 12,908 | 12,542 | 1.336 | 1.336 | 100.000 |
| `skirt_4_panels_1600` | 1,600 | 4 | 8 | 15,140 | 13,854 | 1.334 | 1.334 | 100.000 |
| `skirt_8_panels_1000` | 1,000 | 8 | 16 | 22,669 | 17,814 | 1.332 | 1.333 | 100.000 |
| `tee_2300` | 2,300 | 6 | 12 | 35,166 | 34,051 | 1.339 | 1.338 | 100.000 |
| `tee_sleeveless_1800` | 1,800 | 2 | 4 | 25,737 | 24,786 | 1.341 | 1.341 | 100.000 |
| `wb_dress_sleeveless_2600` | 2,600 | 6 | 12 | 36,784 | 32,812 | 1.351 | 1.351 | 100.000 |
| `wb_pants_straight_1500` | 1,500 | 6 | 12 | 26,036 | 23,860 | 1.367 | 1.364 | 100.000 |

## Lowest-Consistency Samples

| Category | Sample | Sim vertices | Scan vertices | Sim seg | Scan seg | Score |
|---|---|---:|---:|---:|---:|---:|
| `dress_sleeveless_2550` | `dress_sleeveless_WYW61XLHSZ` | 0 | 0 | 0 | 0 | 60.0 |
| `jumpsuit_sleeveless_2000` | `jumpsuit_sleeveless_013H78IH9F` | 0 | 0 | 0 | 0 | 60.0 |
| `dress_sleeveless_2550` | `dress_sleeveless_000YCTJ9HS` | 8,690 | 8,664 | 8,690 | 8,664 | 100.0 |
| `dress_sleeveless_2550` | `dress_sleeveless_02785H9ILO` | 9,674 | 9,674 | 9,674 | 9,674 | 100.0 |
| `dress_sleeveless_2550` | `dress_sleeveless_02SNUB424B` | 10,678 | 10,524 | 10,678 | 10,524 | 100.0 |
| `dress_sleeveless_2550` | `dress_sleeveless_038TR0ANFK` | 5,886 | 5,886 | 5,886 | 5,886 | 100.0 |
| `dress_sleeveless_2550` | `dress_sleeveless_03ATARTQ2Z` | 12,840 | 12,726 | 12,840 | 12,726 | 100.0 |
| `dress_sleeveless_2550` | `dress_sleeveless_03NR4RD224` | 8,940 | 8,940 | 8,940 | 8,940 | 100.0 |
| `dress_sleeveless_2550` | `dress_sleeveless_04I8B5BYZY` | 8,875 | 8,737 | 8,875 | 8,737 | 100.0 |
| `dress_sleeveless_2550` | `dress_sleeveless_063X1Q91RU` | 6,632 | 6,632 | 6,632 | 6,632 | 100.0 |

## Generated Figures

- `fig_mesh_quality_by_category.png`
- `fig_pattern_structure_by_category.png`
- `fig_consistency_histogram.png`
- `fig_skirt_complexity_ladder.png`