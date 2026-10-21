# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Added UI regression tests for History search, empty states, and reopening saved comparisons without retaining another run's evaluations.

## [0.1.0] - 2026-10-17

### Added
- Parallel prompt benchmarks across models through LiteLLM, including key-free Demo models.
- Metrics: latency, time to first token, token usage (with a labelled character-based fallback) and estimated cost. Cost stays unavailable when pricing is unknown, rather than showing zero.
- Evaluations: required/forbidden phrases, regex with a per-pattern timeout, word limits, JSON Schema and an optional LLM-as-a-Judge.
- SQLite run history and a Streamlit comparison UI.
- JSON, CSV and Markdown exports, hardened against spreadsheet formula and Markdown fence injection.
- Security defaults: prompt logging off, custom provider URLs blocked from local and private networks, and secrets redacted from provider errors.
- Docker image and CI quality checks.

### Fixed
- The Streamlit UI tests resolve the app path from the test file, so they pass on newer Streamlit (#3).

### Changed
- GitHub Actions upgraded to the Node 24 majors (#1).
- Tests added for provider retry, request building, chunk parsing, the custom URL guard and secret redaction (#5).
