# Experiment 01 - Full Zenodo Pattern Reconstruction Audit

Goal: run the full downloadable `Dataset of 3D Garments with Sewing Patterns`
experiment for the pattern-reconstruction paper direction.

Pipeline:

1. Fetch the current Zenodo record manifest.
2. Download all 14 archives with resume support.
3. Verify every archive against its Zenodo MD5 checksum.
4. Audit each archive directly in zip form.
5. Export per-sample CSV, per-archive CSV, and JSON summary.

Primary outputs:

- `zenodo_file_manifest.csv`
- `download_status.csv`
- `*_audit.csv`
- `zenodo_full_pattern_audit.csv`
- `summary.json`
- `experiment_summary_extended.json`
- `category_summary.csv`
- `missing_evidence.csv`
- `figures/fig_full_category_render_pattern_evidence.png`
- `figures/fig_full_category_complexity_chart.png`
- `full_experiment.log`

Status command:

```powershell
python scripts\check_full_experiment_status.py
```

This is intentionally a long-running experiment. It favors complete data,
checksums, and resumability over speed.

Current completed run:

- Verified files: 14/14
- Verified compressed bytes: 84,768,495,305
- Audited samples: 22,457
- Production categories: 12
- Complete samples: 22,452
- Samples with missing evidence: 5
