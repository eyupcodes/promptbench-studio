"""Deterministic text evaluators."""

import unicodedata
from uuid import UUID

import regex

from promptbench_studio.domain.schemas import EvaluationConfig, EvaluationResult

REGEX_TIMEOUT_SECONDS = 0.1


def _result(
    run_id: UUID,
    kind: str,
    criterion: str,
    passed: bool,
    explanation: str | None = None,
) -> EvaluationResult:
    return EvaluationResult(
        run_id=run_id,
        evaluator_type=kind,
        criterion=criterion,
        score=float(passed),
        explanation=explanation or ("Passed" if passed else "Failed"),
    )


def _evaluate_regex(run_id: UUID, output: str, pattern: str) -> EvaluationResult:
    try:
        passed = regex.search(pattern, output, timeout=REGEX_TIMEOUT_SECONDS) is not None
    except TimeoutError:
        return _result(run_id, "regex", pattern, False, "Regex evaluation timed out")
    return _result(run_id, "regex", pattern, passed)


def _fold(text: str) -> str:
    """NFKC-normalise and case-fold, so equivalent spellings compare equal."""
    return unicodedata.normalize("NFKC", text).casefold()


def evaluate_rules(run_id: UUID, output: str, config: EvaluationConfig) -> list[EvaluationResult]:
    folded = _fold(output)
    results = [
        _result(run_id, "required_phrase", phrase, _fold(phrase) in folded)
        for phrase in config.required_phrases
    ]
    results.extend(
        _result(run_id, "forbidden_phrase", phrase, _fold(phrase) not in folded)
        for phrase in config.forbidden_phrases
    )
    results.extend(_evaluate_regex(run_id, output, pattern) for pattern in config.regex_patterns)
    word_count = len(output.split())
    if config.min_words is not None:
        results.append(
            _result(run_id, "min_words", str(config.min_words), word_count >= config.min_words)
        )
    if config.max_words is not None:
        results.append(
            _result(run_id, "max_words", str(config.max_words), word_count <= config.max_words)
        )
    return results
