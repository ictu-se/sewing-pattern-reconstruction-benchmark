# Hard Generalization Benchmark Report

This experiment adds harder protocols to the original random stratified split. The goal is to separate easy category recognition from genuine cross-category structural transfer.

## Protocols

- `leave_one_category_out`: train on all categories except one held-out category; evaluate family match and structural reconstruction proxies.
- `paired_transfer`: train on one related category and test on its paired variant, such as base pants to waistband pants.
- `render_noise_stress`: keep the original train/test split but perturb deterministic render descriptors at test time.

## Aggregate Findings

| Protocol | Feature Set | Mean Family Hit | Mean Panel Exact | Mean Stitch Exact | Mean Panel MAE | Mean Stitch MAE |
|---|---|---:|---:|---:|---:|---:|
| leave-one-category-out | structured | 0.2342 | 0.6064 | 0.4987 | 0.6438 | 1.4517 |
| leave-one-category-out | render_pair | 0.5292 | 0.1314 | 0.1529 | 2.9176 | 5.8916 |

## Leave-One-Category-Out Results

| Feature Set | Held-Out Category | Test N | Family Hit | Panel Exact | Stitch Exact | Panel MAE | Stitch MAE |
|---|---|---:|---:|---:|---:|---:|---:|
| `structured` | `dress_sleeveless_2550` | 2550 | 0.0000 | 0.9984 | 0.0000 | 0.0031 | 2.0008 |
| `structured` | `jacket_2200` | 2200 | 0.0109 | 0.0000 | 0.9891 | 1.0109 | 0.0655 |
| `structured` | `jacket_hood_2700` | 2700 | 0.9985 | 0.0000 | 0.0000 | 2.0015 | 6.0000 |
| `structured` | `jumpsuit_sleeveless_2000` | 2000 | 0.0000 | 0.0000 | 0.0000 | 2.0000 | 2.5470 |
| `structured` | `pants_straight_sides_1000` | 1000 | 0.9030 | 0.8890 | 0.0000 | 0.2220 | 2.6360 |
| `structured` | `skirt_2_panels_1200` | 1200 | 0.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| `structured` | `skirt_4_panels_1600` | 1600 | 0.8919 | 1.0000 | 0.0000 | 0.0000 | 2.0000 |
| `structured` | `skirt_8_panels_1000` | 1000 | 0.0010 | 0.0000 | 0.0000 | 1.8710 | 2.1420 |
| `structured` | `tee_2300` | 2300 | 0.0000 | 0.3957 | 0.9996 | 0.6048 | 0.0009 |
| `structured` | `tee_sleeveless_1800` | 1800 | 0.0006 | 0.9994 | 0.9994 | 0.0022 | 0.0044 |
| `structured` | `wb_dress_sleeveless_2600` | 2600 | 0.0000 | 0.9981 | 1.0000 | 0.0019 | 0.0000 |
| `structured` | `wb_pants_straight_1500` | 1500 | 0.0040 | 0.9960 | 0.9960 | 0.0080 | 0.0240 |
| `render_pair` | `dress_sleeveless_2550` | 2550 | 0.5341 | 0.0000 | 0.0000 | 2.1114 | 2.6188 |
| `render_pair` | `jacket_2200` | 2200 | 0.0345 | 0.0000 | 0.9605 | 1.0464 | 0.2227 |
| `render_pair` | `jacket_hood_2700` | 2700 | 0.0026 | 0.0000 | 0.0000 | 6.2922 | 12.5896 |
| `render_pair` | `jumpsuit_sleeveless_2000` | 2000 | 0.0000 | 0.8725 | 0.0000 | 0.2550 | 2.2560 |
| `render_pair` | `pants_straight_sides_1000` | 1000 | 0.9960 | 0.0080 | 0.0000 | 2.4960 | 6.9680 |
| `render_pair` | `skirt_2_panels_1200` | 1200 | 0.9750 | 0.0250 | 0.0250 | 5.8267 | 11.6533 |
| `render_pair` | `skirt_4_panels_1600` | 1600 | 1.0000 | 0.0381 | 0.0000 | 3.8350 | 7.7462 |
| `render_pair` | `skirt_8_panels_1000` | 1000 | 0.9990 | 0.0000 | 0.0000 | 3.5980 | 7.3280 |
| `render_pair` | `tee_2300` | 2300 | 0.1378 | 0.0000 | 0.8474 | 1.4422 | 1.1878 |
| `render_pair` | `tee_sleeveless_1800` | 1800 | 0.3850 | 0.0017 | 0.0017 | 5.2061 | 10.3944 |
| `render_pair` | `wb_dress_sleeveless_2600` | 2600 | 0.3673 | 0.6312 | 0.0004 | 0.7385 | 2.0038 |
| `render_pair` | `wb_pants_straight_1500` | 1500 | 0.9193 | 0.0000 | 0.0000 | 2.1640 | 5.7307 |

## Paired Transfer Results

| Feature Set | Source | Target | Family Hit | Panel Exact | Stitch Exact | Panel MAE | Stitch MAE |
|---|---|---|---:|---:|---:|---:|---:|
| `structured` | `dress_sleeveless_2550` | `wb_dress_sleeveless_2600` | 1.0000 | 0.0000 | 0.0000 | 2.0000 | 2.0000 |
| `structured` | `pants_straight_sides_1000` | `wb_pants_straight_1500` | 1.0000 | 0.0000 | 0.0000 | 2.0000 | 6.0000 |
| `structured` | `jacket_2200` | `jacket_hood_2700` | 1.0000 | 0.0000 | 0.0000 | 2.0000 | 6.0000 |
| `structured` | `tee_2300` | `tee_sleeveless_1800` | 1.0000 | 0.0000 | 0.0000 | 4.0000 | 8.0000 |
| `structured` | `skirt_2_panels_1200` | `skirt_4_panels_1600` | 1.0000 | 0.0000 | 0.0000 | 2.0000 | 4.0000 |
| `structured` | `skirt_4_panels_1600` | `skirt_8_panels_1000` | 1.0000 | 0.0000 | 0.0000 | 4.0000 | 8.0000 |
| `render_pair` | `dress_sleeveless_2550` | `wb_dress_sleeveless_2600` | 1.0000 | 0.0000 | 0.0000 | 2.0000 | 2.0000 |
| `render_pair` | `pants_straight_sides_1000` | `wb_pants_straight_1500` | 1.0000 | 0.0000 | 0.0000 | 2.0000 | 6.0000 |
| `render_pair` | `jacket_2200` | `jacket_hood_2700` | 1.0000 | 0.0000 | 0.0000 | 2.0000 | 6.0000 |
| `render_pair` | `tee_2300` | `tee_sleeveless_1800` | 1.0000 | 0.0000 | 0.0000 | 4.0000 | 8.0000 |
| `render_pair` | `skirt_2_panels_1200` | `skirt_4_panels_1600` | 1.0000 | 0.0000 | 0.0000 | 2.0000 | 4.0000 |
| `render_pair` | `skirt_4_panels_1600` | `skirt_8_panels_1000` | 1.0000 | 0.0000 | 0.0000 | 4.0000 | 8.0000 |

## Render Noise Stress

| Noise Sigma | Top-1 | Family Hit | Panel Exact | Stitch Exact | Panel MAE | Stitch MAE |
|---:|---:|---:|---:|---:|---:|---:|
| 0.00 | 0.9970 | 0.9985 | 0.9973 | 0.9982 | 0.0053 | 0.0113 |
| 0.05 | 0.1253 | 0.2337 | 0.2007 | 0.1793 | 2.6716 | 5.0647 |
| 0.10 | 0.1300 | 0.2450 | 0.2010 | 0.1915 | 2.7069 | 5.0825 |
| 0.20 | 0.1202 | 0.2349 | 0.1850 | 0.1900 | 2.6633 | 4.9899 |
| 0.35 | 0.1200 | 0.2283 | 0.2034 | 0.1948 | 2.6485 | 4.9917 |