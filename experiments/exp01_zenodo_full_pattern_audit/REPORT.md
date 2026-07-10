# Full Zenodo Pattern Reconstruction Experiment Report

## Scope

- Verified archives/files: 14
- Audited samples: 22,457
- Production categories: 12
- Test samples: 7
- Complete samples: 22,452 (99.9777%)
- Samples with missing evidence: 5

## Category Summary

| Category | N | Complete | C mean | Sim V mean | Sim F mean | Sim F p95 | Panels | Edges | Stitches | SVG |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dress_sleeveless_2550 | 2,550 | 2,547 | 99.965 | 9083.8 | 17893.8 | 27575 | 4.00 | 29.00 | 10.00 | 4.00 |
| jacket_2200 | 2,200 | 2,200 | 100.000 | 17801.1 | 35060.3 | 58294 | 7.00 | 36.00 | 12.00 | 7.00 |
| jacket_hood_2700 | 2,700 | 2,700 | 100.000 | 19144.7 | 37743.2 | 61580 | 9.00 | 47.00 | 18.00 | 9.00 |
| jumpsuit_sleeveless_2000 | 2,000 | 1,999 | 99.967 | 8448.8 | 16681.6 | 23855 | 6.00 | 39.00 | 14.00 | 6.00 |
| pants_straight_sides_1000 | 1,000 | 1,000 | 100.000 | 6068.2 | 11991.8 | 19098 | 4.00 | 20.00 | 6.00 | 4.00 |
| skirt_2_panels_1200 | 1,200 | 1,200 | 100.000 | 6555.9 | 12908.1 | 21523 | 2.00 | 12.00 | 4.00 | 2.00 |
| skirt_4_panels_1600 | 1,600 | 1,600 | 100.000 | 7699.3 | 15140.0 | 25674 | 4.00 | 24.00 | 8.00 | 4.00 |
| skirt_8_panels_1000 | 1,000 | 999 | 99.989 | 11510.0 | 22668.9 | 40036 | 8.00 | 48.00 | 16.00 | 8.00 |
| tee_2300 | 2,300 | 2,300 | 100.000 | 17780.9 | 35166.5 | 57362 | 6.00 | 33.00 | 12.00 | 6.00 |
| tee_sleeveless_1800 | 1,800 | 1,800 | 100.000 | 13051.2 | 25737.4 | 46025 | 2.00 | 17.00 | 4.00 | 2.00 |
| test | 7 | 7 | 100.000 | 11793.9 | 23245.3 | 44616 | 6.57 | 36.86 | 13.71 | 6.57 |
| wb_dress_sleeveless_2600 | 2,600 | 2,600 | 100.000 | 18558.5 | 36784.5 | 58923 | 6.00 | 33.00 | 12.00 | 6.00 |
| wb_pants_straight_1500 | 1,500 | 1,500 | 100.000 | 13112.7 | 26036.0 | 41240 | 6.00 | 30.00 | 12.00 | 6.00 |

## Missing Evidence

Missing evidence is rare and concentrated in three categories. See `missing_evidence.csv` for sample IDs.

- `has_back`: 2
- `has_front`: 5
- `has_scan_obj`: 2
- `has_scan_seg`: 2
- `has_sim_obj`: 2
- `has_sim_seg`: 2

## Interpretation

The full audit confirms that the dataset provides large-scale paired sewing-pattern, render, segmentation, and mesh evidence suitable for a pattern-reconstruction paper. The category spread covers simple skirts, pants, sleeveless tops, tees, dresses, jumpsuits, jackets, hooded jackets, and waistband variants. Pattern complexity grows from 2-panel skirts to 9-panel hooded jackets, while mesh complexity ranges from roughly 12k simulated faces for simple pants to more than 37k faces for hooded jackets.

The next experimental layer should use these verified categories to define train/test tasks, such as image-to-pattern retrieval, pattern-structure prediction, or parametric pattern generation. This audit supplies the full-data manifest and category statistics needed to choose balanced splits and difficulty levels.
