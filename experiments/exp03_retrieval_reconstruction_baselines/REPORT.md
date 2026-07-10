# Retrieval and Reconstruction Baseline Report

This experiment uses the full quantitative feature table to create stratified train/validation/test splits and evaluate nearest-neighbor retrieval baselines. The retrieved neighbor is also treated as a simple reconstruction baseline for predicting panel and stitch counts.

## Split Summary

| Category | Train | Val | Test | Total |
|---|---:|---:|---:|---:|
| `dress_sleeveless_2550` | 1785 | 382 | 383 | 2550 |
| `jacket_2200` | 1540 | 330 | 330 | 2200 |
| `jacket_hood_2700` | 1890 | 405 | 405 | 2700 |
| `jumpsuit_sleeveless_2000` | 1400 | 300 | 300 | 2000 |
| `pants_straight_sides_1000` | 700 | 150 | 150 | 1000 |
| `skirt_2_panels_1200` | 840 | 180 | 180 | 1200 |
| `skirt_4_panels_1600` | 1120 | 240 | 240 | 1600 |
| `skirt_8_panels_1000` | 700 | 150 | 150 | 1000 |
| `tee_2300` | 1610 | 345 | 345 | 2300 |
| `tee_sleeveless_1800` | 1260 | 270 | 270 | 1800 |
| `wb_dress_sleeveless_2600` | 1820 | 390 | 390 | 2600 |
| `wb_pants_straight_1500` | 1050 | 225 | 225 | 1500 |

## Baseline Results

| Baseline | Features | Test N | Top-1 | Top-5 | MRR | Panel MAE | Stitch MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| `random_category` | 0 | 3368 | 0.0814 | 0.4167 | 0.0000 | 0.0000 | 0.0000 |
| `majority_category` | 0 | 3368 | 0.1202 | 0.5502 | 0.0000 | 0.0000 | 0.0000 |
| `nn_pattern` | 9 | 3368 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| `nn_mesh` | 14 | 3368 | 0.7732 | 0.9543 | 0.8504 | 0.6642 | 1.4264 |
| `nn_segmentation` | 8 | 3368 | 0.8812 | 0.9774 | 0.9235 | 0.0050 | 0.1010 |
| `nn_combined` | 31 | 3368 | 0.9997 | 0.9997 | 0.9997 | 0.0009 | 0.0018 |