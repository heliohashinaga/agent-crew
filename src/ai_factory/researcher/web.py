"""Deterministic ``web`` scope core (T014, Option D, multi-angle best-per-angle).

The ``web`` scope is layered on **injected** collaborators so it is fully
testable with fakes and never touches the network in unit tests:

- :class:`WebFetcher` — returns candidate URLs for a search angle.
- :class:`ContentFetcher` — returns page text for a URL.
- an :class:`~ai_factory.shared.llm.provider.LLMProvider` — ranks candidates
  (best-per-angle) and synthesizes a concise summary.

Workflow (Option D):

1. Expand the query into 2-4 **search angles** (static, deterministic).
2. For each angle, fetch candidate URLs via :class:`WebFetcher`.
3. Rank each angle's candidates by source quality via the LLM and keep the
   **best** URL per angle.
4. Fetch page content of the selected URLs via :class:`ContentFetcher`.
5. Synthesize one concise summary via the LLM, capped by a configurable
   **context-window limit**.

On any fetch/LLM failure that leaves the lookup without a usable source the
core raises :class:`~ai_factory.researcher.agent.ResearcherWebError` — it
never silently returns an empty result.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ai_factory.researcher.agent import ResearcherWebError
from ai_factory.researcher.models import ResearchResult, ResearchSource
from ai_factory.shared.llm.provider import LLMMessage, LLMProvider

# Default angle expansion: 2-4 turns on the query shaped as a search engine
# query (Option D). Kept static and deterministic (no LLM in the expansion).
_DEFAULT_ANGLES = 4

# Hard cap on the total content fed to the summarizer (context window).
_DEFAULT_CONTEXT_WINDOW = 2048

# Cap on how much raw content is fetched per URL before summarization.
_MAX_FETCH_CHARS = 4000


class WebFetcher(ABC):
    """Injectable source of candidate URLs for a search angle."""

    @abstractmethod
    def query(self, angle: str) -> list[str]:
        """Return zero or more candidate URLs for ``angle``."""
        raise NotImplementedError


class ContentFetcher(ABC):
    """Injectable fetcher of readable page text for a URL."""

    @abstractmethod
    def fetch(self, url: str) -> str:
        """Return the readable text at ``url`` (may be empty)."""
        raise NotImplementedError


class UrllibWebFetcher(WebFetcher):
    """Real, network-bound candidate source via ``urllib`` (T015)."""

    def __init__(self, endpoint: str | None = None) -> None:
        self._endpoint = endpoint

    def query(self, angle: str) -> list[str]:
        """Return a small set of candidate URLs for ``angle`` (best-effort)."""
        if self._endpoint:
            return [self._endpoint]
        # Fall back to a Google search-accessible URL (best-effort).
        from urllib.parse import quote

        return [f"https://www.google.com/search?q={quote(angle)}"]


class UrllibContentFetcher(ContentFetcher):
    """Real, network-bound page fetch via ``urllib`` (T015)."""

    def __init__(self, timeout_s: float = 10.0) -> None:
        self._timeout_s = timeout_s

    def fetch(self, url: str) -> str:
        """Fetch ``url`` and return readable text (clipped for summarization)."""
        import urllib.request

        req = urllib.request.Request(
            url, headers={"User-Agent": "ai-factory-researcher/0.1"}
        )
        with urllib.request.urlopen(req, timeout=self._timeout_s) as resp:
            data = resp.read(_MAX_FETCH_CHARS)
        text = data.decode("utf-8", errors="replace")
        return _strip_html(text)[:_MAX_FETCH_CHARS]


def _strip_html(text: str) -> str:
    """Very small, dependency-free HTML-to-text approximation for fetching."""
    import html as html_module
    import re

    text = re.sub(r"(?is)<script.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return html_module.unescape(re.sub(r"\s+", " ", text)).strip()


def _expand_angles(query: str) -> list[str]:
    """Expand ``query`` into 2-4 deterministic search angles (Option D)."""
    terms = [t for t in query.split() if t]
    if not terms:
        return [query]
    base = " ".join(terms)
    # Deterministic, static turns on the same query terms (no LLM involved).
    angles = [base]
    for wrapped in (
        " and ".join(terms),
        " ".join(terms) + " best practices",
        " ".join(terms) + " documentation",
    ):
        angles.append(wrapped)
    # Deduplicate preserving order, bounded to [2, min(_DEFAULT_ANGLES, n)].
    seen: set[str] = set()
    deduped: list[str] = []
    for angle in angles:
        if angle and angle not in seen:
            seen.add(angle)
            deduped.append(angle)
    if len(deduped) < 2:
        return deduped
    return deduped[: _DEFAULT_ANGLES]


def _extract_url(text: str, candidates: list[str]) -> str | None:
    """Pick the candidate URL the LLM chose from ``text``, else the first."""
    for cand in candidates:
        if cand in text:
            return cand
    return candidates[0] if candidates else None


def _rank_best_per_angle(
    provider: LLMProvider, angle: str, candidates: list[str]
) -> str | None:
    """Rank ``candidates`` by source quality via the LLM; return the best URL."""
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    prompt = (
        f"Rank these web sources for relevance to '{angle}' by quality. "
        "Return the single best URL verbatim.\n" + "\n".join(candidates)
    )
    result = provider.complete(
        [LLMMessage(role="user", content=prompt)], instruction="best-per-angle"
    )
    return _extract_url(result.content, candidates)


def _summarize(provider: LLMProvider, query: str, content: str) -> str:
    """Synthesize a concise summary of ``content`` for ``query`` via the LLM."""
    clipped = content[:_MAX_FETCH_CHARS] if content else ""
    prompt = (
        f"Synthesize a concise research summary (fits a small context window) "
        f"for the query '{query}' from this web content:\n\n{clipped}"
    )
    result = provider.complete(
        [LLMMessage(role="user", content=prompt)], instruction="summarize"
    )
    return result.content.strip()


def web_lookup(
    query: str,
    *,
    llm: LLMProvider,
    fetcher: WebFetcher,
    content_fetcher: ContentFetcher,
    angles: list[str] | None = None,
    context_window: int = _DEFAULT_CONTEXT_WINDOW,
) -> ResearchResult:
    """Run a multi-angle best-per-angle web lookup over injected collaborators.

    Returns a :class:`ResearchResult` with best-per-angle URL ``sources`` and a
    concise LLM-synthesized ``summary``. Raises :class:`ResearcherWebError` on
    any fetch/LLM failure that prevents producing results (never silently
    empty) or when the query has no usable content.
    """
    try:
        angle_names = angles or _expand_angles(query)
        if context_window <= 0:
            context_window = _DEFAULT_CONTEXT_WINDOW

        url_to_source: dict[str, str] = {}
        # Best-per-angle: fetch candidates per angle, rank, keep one per angle.
        for angle in angle_names[: _DEFAULT_ANGLES]:
            try:
                candidates = fetcher.query(angle)
            except Exception as exc:  # noqa: BLE001 - surface as web error
                raise ResearcherWebError(
                    f"web fetcher failed for angle {angle!r}: {exc}"
                ) from exc
            if not candidates:
                continue
            best = _rank_best_per_angle(llm, angle, candidates)
            if best:
                url_to_source.setdefault(best, angle)

        if not url_to_source:
            raise ResearcherWebError(
                "web lookup produced no source candidates; cannot summarize."
            )

        # Fetch content and synthesize a summary within the context window.
        combined: list[str] = []
        for url in list(url_to_source):
            try:
                text = content_fetcher.fetch(url)
            except Exception as exc:  # noqa: BLE001 - surface as web error
                raise ResearcherWebError(
                    f"web content fetch failed for {url}: {exc}"
                ) from exc
            if text:
                window = context_window // max(len(url_to_source), 1)
                combined.append(text[:window])

        summary = _summarize(llm, query, "\n\n".join(combined)) if combined else ""

        sources = [
            ResearchSource(path=url, lines=None, snippet=None)
            for url in url_to_source
        ]
        return ResearchResult(
            query=query,
            summary=summary,
            sources=sources,
            scopes_used=["web"],
        )
    except ResearcherWebError:
        raise
    except Exception as exc:  # noqa: BLE001 - never silently empty
        raise ResearcherWebError(f"web lookup failed: {exc}") from exc
