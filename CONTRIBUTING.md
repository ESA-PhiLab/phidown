# Contributing

Contributions to `phidown` are welcome.

## Development Setup

Clone the repository and install a local environment with one of the supported
workflows:

```bash
git clone https://github.com/ESA-PhiLab/phidown.git
cd phidown

# Option 1: uv
uv sync --extra test --extra docs

# Option 2: PDM
pdm install
```

If you prefer editable `pip` installs:

```bash
pip install -e ".[dev,test,docs,viz,ais]"
```

## Validation

Run the test suite:

```bash
uv run --extra test pytest -q
```

Or, if you are using another environment manager:

```bash
pytest -q
```

Linting:

```bash
flake8 phidown tests
```

Build the docs:

```bash
cd docs
python3 -m pip install -r requirements.txt
make html
```

## Pull Requests

Before opening a pull request:

- Keep the change focused and well-scoped.
- Add or update tests when behavior changes.
- Update documentation for user-facing changes.
- Include a concise summary of what changed, why it changed, and how you
  verified it.

For bugs and questions, use:

- Issues: <https://github.com/ESA-PhiLab/phidown/issues>
- Discussions: <https://github.com/ESA-PhiLab/phidown/discussions>
