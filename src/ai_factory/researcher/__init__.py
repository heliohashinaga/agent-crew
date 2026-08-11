"""Researcher role library (mono-capacity, fixed).

A Library-First lookup library the principal roles (planner/coder/tester/
reviewer) invoke to query the repository (``repo``, deterministic) and the web
(``web``, Option D multi-angle best-per-angle in v1) and receive a concise,
sourced :class:`~ai_factory.researcher.models.ResearchResult`.
"""

from ai_factory.researcher.agent import ResearcherWebError, lookup
from ai_factory.researcher.models import ResearchResult, ResearchSource

__all__ = ["lookup", "ResearchResult", "ResearchSource", "ResearcherWebError"]
