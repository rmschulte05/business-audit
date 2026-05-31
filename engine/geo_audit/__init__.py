"""Deterministic GEO audit engine.

This package turns the GEO score from an LLM opinion into a reproducible,
evidence-based measurement. It collects objectively measurable signals from a
website (HTTP headers, robots.txt, raw HTML, JSON-LD, llms.txt, optional
PageSpeed data) and scores them in code against fixed thresholds.

Design contract:
- Every signal is either MEASURED (real evidence captured) or NOT_MEASURED
  (we could not observe it). NOT_MEASURED signals never fabricate a value and
  never penalize the score — they only lower the confidence band.
- Scoring is pure: the same evidence always produces the same score.
- The LLM skills consume this evidence instead of guessing.
"""

__version__ = "2.0.0"
