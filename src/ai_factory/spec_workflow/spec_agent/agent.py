"""Spec-agent role library (T017, FR-002/003/006).

The spec-agent drafts a :class:`SpecVersion` from a :class:`FeatureRequest`:
intent, rationale, acceptance criteria (FR-003), definition of done and edge
cases, and it surfaces *bounded* clarifications for scope-critical ambiguity
(FR-006).

The core is a deterministic, network-free function (:func:`draft_spec`) so it
is unit/contract-testable without an LLM. An :class:`LLMProvider` may be
supplied for enrichment, but the library never *requires* network access
(constitution III/IV).
"""

from __future__ import annotations

from ai_factory.shared.llm.provider import LLMProvider
from ai_factory.shared.spec_store.models import (
    AcceptanceCriterion,
    Assumption,
    Clarification,
    EdgeCase,
    FeatureRequest,
    SpecVersion,
)

# Bounded clarification cap (FR-006): never surface an unbounded list.
_MAX_CLARIFICATIONS = 3


def _derive_rationale(request: FeatureRequest) -> str:
    if request.constraints:
        return "Deliver: " + "; ".join(request.constraints)
    return f"Implement the requested capability: {_sentence(request.raw_text)}"


def _derive_ac(request: FeatureRequest) -> list[AcceptanceCriterion]:
    """Turn constraints into testable acceptance criteria (FR-003)."""
    acs: list[AcceptanceCriterion] = []
    for constraint in request.constraints:
        acs.append(
            AcceptanceCriterion(
                statement=f"Given the requested capability, {_sentence(constraint)}",
                verified_by="automated test",
            )
        )
    if not acs:
        # Fallback: derive one AC from the intent itself so FR-003 holds even
        # when no constraints were supplied.
        acs.append(
            AcceptanceCriterion(
                statement=f"Given a user with access, {_sentence(request.raw_text)}",
                verified_by="manual inspection",
            )
        )
    return acs


def _derive_dod(request: FeatureRequest) -> str:
    if request.constraints:
        return "All supplied constraints are met and acceptance criteria pass."
    return "Acceptance criteria pass and behaviour is documented."


def _derive_edge_cases(request: FeatureRequest) -> list[EdgeCase]:
    """Derive bounded edge cases from scope-critical keywords (FR-006)."""
    text = request.raw_text.lower()
    cases: list[EdgeCase] = []
    if any(k in text for k in ("empty", "blank", "no ", "missing")):
        cases.append(
            EdgeCase(
                description="Empty/blank input", expected_behavior="Graceful rejection"
            )
        )
    if any(
        k in text for k in ("expire", "timeout", "session", "30 minutes", "60 minutes")
    ):
        cases.append(
            EdgeCase(
                description="Expiry/timeout boundary",
                expected_behavior="Session ends at threshold",
            )
        )
    if any(k in text for k in ("duplicate", "again", "repeat", "already")):
        cases.append(
            EdgeCase(
                description="Duplicate submission",
                expected_behavior="Idempotent handling",
            )
        )
    return cases


def _bounded_clarifications(request: FeatureRequest) -> list[Clarification]:
    """Surface clarifications only for scope-critical ambiguity (FR-006)."""
    clarifications: list[Clarification] = []
    if not request.constraints:
        clarifications.append(
            Clarification(
                question=(
                    "No acceptance criteria were provided. "
                    "What are the must-have behaviours?"
                ),
                suggested_options=["Recommended defaults", "I will list them"],
                affects_section="acceptance_criteria",
            )
        )
    # Conflicting constraints trigger a clarification.
    seen: set[str] = set()
    for c in request.constraints:
        token = c.split()[0].lower() if c.split() else ""
        if token and token in seen:
            clarifications.append(
                Clarification(
                    question=(
                        f"Conflicting constraints reference '{token}'. "
                        "Which takes precedence?"
                    ),
                    suggested_options=["First wins", "Last wins"],
                    affects_section="constraints",
                )
            )
            break
        seen.add(token)
    return clarifications[:_MAX_CLARIFICATIONS]


def _sentence(text: str) -> str:
    text = text.strip()
    if not text:
        return "the requested capability"
    return text[:-1].rstrip() + "." if text.endswith(".") else text


def draft_spec(
    request: FeatureRequest,
    provider: LLMProvider | None = None,
    feedback: str = "",
) -> SpecVersion:
    """Draft a :class:`SpecVersion` from ``request``.

    ``feedback`` carries reviewer notes for the amend loop (an empty string
    means a fresh draft). ``provider`` is reserved for optional LLM
    enrichment; the deterministic core is fully network-free.
    """
    if feedback:
        rationales = [f"Revised: {feedback.strip()}"]
        if _derive_rationale(request):
            rationales.append(_derive_rationale(request))
        rationale = " ".join(r for r in rationales if r)
    else:
        rationale = _derive_rationale(request)

    acs = _derive_ac(request)
    spec = SpecVersion(
        intent=_sentence(request.raw_text),
        rationale=rationale,
        acceptance_criteria=acs,
        definition_of_done=_derive_dod(request),
        edge_cases=_derive_edge_cases(request),
        clarifications=_bounded_clarifications(request),
    )
    if provider is not None:
        spec.assumptions.append(
            Assumption(
                assumption="Specification drafted with augmented analysis",
                rationale="provider path",
            )
        )
    return spec


__all__ = ["draft_spec"]
