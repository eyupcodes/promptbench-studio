# PromptBench Studio

Open-source workspace for comparing multiple LLMs under same prompt, parameters, and evaluation criteria.

> Status: working MVP. APIs and storage schema may change before `1.0`.

## MVP capabilities

- Parallel benchmarks through LiteLLM
- Latency, time-to-first-token, token, and estimated-cost metrics
- Rule, JSON Schema, manual, and LLM-as-a-Judge evaluations
- SQLite run history
- Streamlit comparison UI
- JSON, CSV, and Markdown exports

Full product brief: [PromptBench_Studio.md](PromptBench_Studio.md).

## Requirements

- Python 3.12+
- Provider API key for live calls; built-in Demo models and tests require no key

## Local setup

```bash
python -m venv .venv
.venv/Scripts/activate
python -m pip install -e ".[dev]"
copy .env.example .env
streamlit run src/promptbench_studio/ui/main.py
```

On macOS/Linux, activate with `source .venv/bin/activate` and copy with `cp`.

## Quick demo

Start app, open **New Benchmark**, and keep default Demo models selected. Demo runs are deterministic, local, and free; no provider keys or network access required. Select live models only after configuring matching environment keys.

## Supported metrics and evaluation

- Latency and time to first token
- Provider token usage, with transparent character-based fallback when usage is unavailable
- Estimated cost; unknown pricing stays unavailable instead of becoming zero
- Required/forbidden phrases, regex, word limits, JSON Schema, and optional LLM judge
- CSV, JSON, and Markdown exports with spreadsheet and Markdown fence hardening

## Quality checks

```bash
ruff format --check .
ruff check .
mypy
pytest --cov --cov-report=term-missing
```

## Docker

```bash
copy .env.example .env
docker compose up --build
```

Open <http://localhost:8501>.

## Security

- Never commit `.env` or real provider credentials.
- Prompt and model output may contain sensitive data. Prompt logging defaults to off.
- Review exported benchmark data before sharing it.
- Custom provider URLs are validated to block local and private network targets.
- User regex evaluation has a per-pattern timeout to limit catastrophic backtracking.
- Provider errors pass through secret redaction before persistence or display.

Report vulnerabilities privately through GitHub Security Advisories after repository publication.

## MVP limits

- Single-user local workspace; no authentication or multi-tenant isolation
- Live provider credentials remain environment-only and require app restart after changes
- Token fallback is an estimate, not provider billing data
- Manual scoring, semantic similarity, dataset batches, and cross-run consistency analytics remain future work
- SQLite suits local use; production deployments need database and operational hardening
- Custom URL validation cannot fully eliminate DNS rebinding between validation and request dispatch
- UI page-level automated coverage remains thinner than service/domain coverage

## License

Apache License 2.0. See [LICENSE](LICENSE).
