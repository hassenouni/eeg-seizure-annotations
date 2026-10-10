# Contributing

Install the shared dependencies described in the README, then this project with
`python -m pip install -e ".[dev]"`. Run `python -m pytest`,
`python -m ruff check src tests examples` and `python -m ruff format --check src tests examples`.
Include a small behavioral regression test when fixing a scientific or data-format bug.
Use synthetic fixtures in tests; keep private data, absolute local paths and fitted
checkpoints out of contributions. Explain units, shape contracts and boundary choices.
Do not add clinical performance claims without a separately reviewed experiment.
