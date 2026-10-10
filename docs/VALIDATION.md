# Local software verification

Verified on 2026-10-10, Windows / Python 3.10, in the portfolio virtual environment.

- 8 pytest cases passed.
- Ruff lint and format checks passed for src, tests and examples.
- Synthetic demo passed.
- Demo using an original 8-second, four-channel CHB-MIT excerpt passed.
- Demo using an original 8-second, four-channel Siena excerpt passed.
- Editable package build and installation succeeded.

The evaluator uses synthetic events even when loading a real excerpt; it does not
compute dataset detection metrics. The ML demo constructs an unfitted pipeline.
Deep-learning demos use untrained forward passes. Tiny synthetic fitting/gradient
checks exist only in unit tests. No patient-data model was trained.

Scientific dependencies were inherited from the existing Python installation;
a fresh isolated dependency installation and remote GitHub Actions have not been
verified. The CI template uses versioned shared-package GitHub tags. It is retained in
`docs/ci/tests.yml` pending the GitHub workflow permission; no remote CI run is claimed.
Local sample data and manifests are excluded from Git. Full EDFs were not copied.

Reproduce with the commands in the repository README. These checks establish
software behavior on small examples, not clinical or experimental performance.
