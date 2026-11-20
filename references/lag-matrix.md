# Publication Lag Matrix

Working priors. Override per deployment; these are starting estimates,
not measured ground truth — validate against your own domains before
relying on them in production.

The canonical machine-readable lag priors live in `references/lag_matrix.json`
and are loaded directly by `scripts/lag_prior.py` and `scripts/staleness_score.py`.
Edit `references/lag_matrix.json` to adjust `min_months`, `typical_months`,
`max_months`, or `fresh_window_seconds` for any `info_type`.
