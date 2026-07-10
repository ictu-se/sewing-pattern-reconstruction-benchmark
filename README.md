# Sewing Pattern Reconstruction Benchmark

This repository contains the reproducible code and experiment artifacts for a full-data sewing-pattern reconstruction benchmark on the Dataset of 3D Garments with Sewing Patterns.

The benchmark audits 22,457 structured garment samples directly from the verified Zenodo archives, computes pattern, mesh, segmentation, and consistency metrics for the 22,450-sample production subset, and evaluates deterministic retrieval-style reconstruction baselines. It also includes hard-generalization protocols for leave-one-category-out transfer, paired template transfer, and render descriptor noise stress testing.

## Repository Layout

- `scripts/`: Python scripts for downloading/verifying Zenodo archives, auditing evidence, computing quantitative metrics, running retrieval baselines, generating figures, and running hard-generalization experiments.
- `experiments/`: Inspectable experiment outputs, summaries, tables, reports, and generated figures.

## Data

The raw dataset archives are not included in this repository because the verified compressed corpus is about 84.77 GB. Download the source data from:

https://zenodo.org/records/5267549

Place the Zenodo archives under:

```text
raw/zenodo_3d_garments_sewing_patterns/archives/
```

The scripts expect this dataset layout when rerunning the full audit and render-based experiments.

## Environment

The experiments use Python 3.10+ and standard scientific/image-processing packages.

```bash
pip install -r requirements.txt
```

## Main Reproduction Commands

Run the full audit and benchmark stages from the repository root:

```bash
python scripts/download_zenodo_full.py
python scripts/run_full_experiment.py
python scripts/run_quantitative_benchmarks.py
python scripts/run_retrieval_baselines.py
python scripts/run_render_image_baselines.py
python scripts/run_hard_generalization_benchmarks.py
```

The render-image baseline requires the raw Zenodo archives. Structured-feature retrieval can be rerun after the quantitative benchmark tables have been generated.

## Notes

The repository intentionally separates raw data from reproducible experiment outputs. Heavy raw archives, feature caches, local logs, LaTeX auxiliary files, and process state files are excluded.
