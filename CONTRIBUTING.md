# Contributing

## Development

1. Create a Python 3.12 virtual environment.
2. Install `python -m pip install -e ".[dev]"`.
3. Add behavior tests before implementation changes.
4. Run:

```bash
ruff format --check .
ruff check .
mypy
pytest --cov --cov-report=term-missing
```

Keep functions focused, validate external input, and never commit credentials or runtime databases.

## Pull requests

Describe user-visible behavior, security impact, and test evidence. Keep unrelated changes separate. Report security vulnerabilities privately rather than opening a public issue.
