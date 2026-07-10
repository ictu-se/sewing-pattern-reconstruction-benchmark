# Render Image Retrieval Baseline Report

This experiment extracts deterministic image descriptors from front/back garment renders and evaluates nearest-neighbor retrieval on the same stratified split used by the structured-feature baselines.

## Scope

- Samples with feature rows: 22,450
- Missing front renders: 5
- Missing back renders: 2

## Results

| Baseline | Features | Train | Test | Top-1 | Top-5 | MRR | Panel MAE | Stitch MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `nn_render_front` | 375 | 15715 | 3368 | 0.9973 | 0.9997 | 0.9985 | 0.0059 | 0.0089 |
| `nn_render_back` | 375 | 15715 | 3368 | 0.9973 | 0.9994 | 0.9983 | 0.0062 | 0.0101 |
| `nn_render_pair` | 1125 | 15715 | 3368 | 0.9970 | 0.9997 | 0.9983 | 0.0053 | 0.0113 |