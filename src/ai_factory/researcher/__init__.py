"""Researcher role library (mono-capacity, fixed).

A Library-First lookup library the principal roles (planner/coder/tester/
reviewer) invoke to query the repository (``repo``, deterministic) and the web
(``web``, Option D multi-angle best-per-angle in v1) and receive a concise,
sourced :class:`~ai_factory.researcher.models.ResearchResult`.
"""

from ai_factory.researcher.agent import ResearcherWebError, lookup
from ai_factory.researcher.models import ResearchResult, ResearchSource
from ai_factory.researcher.profile import (
    MAX_ANGLES,
    MIN_ANGLES,
    RESEARCHER_PROFILE,
    RESEARCHER_ROLE,
    ResearcherProfile,
)

__all__ = [
    "lookup",
    "ResearchResult",
    "ResearchSource",
    "ResearcherWebError",
    "RESEARCHER_PROFILE",
    "RESEARCHER_ROLE",
    "ResearcherProfile",
    "MIN_ANGLES",
    "MAX_ANGLES",
]
