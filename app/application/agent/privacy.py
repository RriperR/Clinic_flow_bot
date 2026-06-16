from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.domain.entities import Worker

_TOKEN_RE = re.compile(r"[0-9A-Za-zА-Яа-яЁё]+")
_SPACE_RE = re.compile(r"\s+")
_SHIFT_MARKERS = (
    "смен",
    "слот",
    "запис",
    "запиш",
    "свобод",
    "врач",
    "доктор",
)


@dataclass(frozen=True)
class ShiftTarget:
    ref: str
    worker_id: int
    label: str


@dataclass(frozen=True)
class ShiftTargetCandidate:
    worker_id: int
    label: str
    score: float


@dataclass(frozen=True)
class SanitizedAgentMessage:
    text: str
    targets: dict[str, ShiftTarget]
    ambiguous_ref: str | None = None
    candidates: tuple[ShiftTargetCandidate, ...] = ()
    needs_target_clarification: bool = False

    @property
    def is_ambiguous(self) -> bool:
        return self.ambiguous_ref is not None and bool(self.candidates)


@dataclass(frozen=True)
class _Token:
    raw: str
    normalized: str
    start: int
    end: int


@dataclass(frozen=True)
class _Match:
    start: int
    end: int
    text: str
    candidates: tuple[ShiftTargetCandidate, ...]

    @property
    def score(self) -> float:
        return self.candidates[0].score if self.candidates else 0.0


def normalize_private_text(value: str | None) -> str:
    normalized = (value or "").replace("ё", "е").replace("Ё", "Е").casefold()
    normalized = re.sub(r"[^0-9a-zа-я]+", " ", normalized)
    return _SPACE_RE.sub(" ", normalized).strip()


class ShiftTargetResolver:
    def sanitize(self, text: str, workers: Sequence[Worker]) -> SanitizedAgentMessage:
        tokens = self._tokenize(text)
        matches = self._all_matches(tokens, workers)
        if not matches:
            return SanitizedAgentMessage(
                text=text,
                targets={},
                needs_target_clarification=self._looks_like_shift_target_request(text),
            )

        sanitized_text = text
        targets: dict[str, ShiftTarget] = {}
        ambiguous_ref: str | None = None
        ambiguous_candidates: tuple[ShiftTargetCandidate, ...] = ()
        for index, match in enumerate(reversed(matches), start=1):
            ref = f"[SHIFT_TARGET_{len(matches) - index + 1}]"
            sanitized_text = f"{sanitized_text[: match.start]}{ref}{sanitized_text[match.end :]}"
            if self._is_ambiguous(match.candidates):
                ambiguous_ref = ref
                ambiguous_candidates = match.candidates
                continue
            targets[ref] = ShiftTarget(
                ref=ref,
                worker_id=match.candidates[0].worker_id,
                label=match.candidates[0].label,
            )

        if ambiguous_ref:
            return SanitizedAgentMessage(
                text=sanitized_text,
                targets={},
                ambiguous_ref=ambiguous_ref,
                candidates=ambiguous_candidates,
            )

        return SanitizedAgentMessage(text=sanitized_text, targets=targets)

    def _tokenize(self, text: str) -> list[_Token]:
        return [
            _Token(
                raw=match.group(0),
                normalized=normalize_private_text(match.group(0)),
                start=match.start(),
                end=match.end(),
            )
            for match in _TOKEN_RE.finditer(text)
        ]

    def _all_matches(self, tokens: list[_Token], workers: Sequence[Worker]) -> list[_Match]:
        candidates = self._candidate_matches(tokens, workers)
        selected: list[_Match] = []
        occupied: set[int] = set()
        for match in sorted(candidates, key=lambda item: (-item.score, -(item.end - item.start))):
            covered = set(range(match.start, match.end))
            if occupied.intersection(covered):
                continue
            selected.append(match)
            occupied.update(covered)
        return sorted(selected, key=lambda item: item.start)

    def _candidate_matches(self, tokens: list[_Token], workers: Sequence[Worker]) -> list[_Match]:
        matches: list[_Match] = []
        max_window = min(4, len(tokens))
        for start_index in range(len(tokens)):
            for size in range(1, max_window + 1):
                end_index = start_index + size
                if end_index > len(tokens):
                    continue
                phrase = " ".join(token.normalized for token in tokens[start_index:end_index])
                if not self._can_match_phrase(phrase):
                    continue
                candidates = self._rank_candidates(phrase, workers)
                if not candidates:
                    continue
                match = _Match(
                    start=tokens[start_index].start,
                    end=tokens[end_index - 1].end,
                    text=phrase,
                    candidates=tuple(candidates),
                )
                matches.append(match)
        return matches

    def _rank_candidates(self, phrase: str, workers: Sequence[Worker]) -> list[ShiftTargetCandidate]:
        ranked: list[ShiftTargetCandidate] = []
        threshold = 0.74 if " " not in phrase else 0.82
        for worker in workers:
            if worker.id is None:
                continue
            score = max((self._score(phrase, alias) for alias in self._aliases(worker.full_name)), default=0.0)
            if score >= threshold:
                ranked.append(ShiftTargetCandidate(worker_id=worker.id, label=worker.full_name, score=score))
        ranked.sort(key=lambda item: (-item.score, item.label))
        return ranked[:5]

    def _aliases(self, full_name: str) -> set[str]:
        normalized = normalize_private_text(full_name)
        parts = [part for part in normalized.split() if len(part) >= 3]
        aliases = {normalized}
        aliases.update(parts)
        if len(parts) >= 2:
            aliases.add(" ".join(parts[:2]))
            aliases.add(f"{parts[0]} {parts[1][0]}")
        if len(parts) >= 3:
            aliases.add(f"{parts[0]} {parts[1][0]} {parts[2][0]}")
        return {alias for alias in aliases if alias}

    def _score(self, phrase: str, alias: str) -> float:
        if phrase == alias:
            return 1.0
        if len(phrase) >= 4 and (phrase in alias or alias in phrase):
            return 0.94
        return SequenceMatcher(None, phrase, alias).ratio()

    def _can_match_phrase(self, phrase: str) -> bool:
        if not phrase or any(marker in phrase for marker in _SHIFT_MARKERS):
            return False
        return any(len(part) >= 4 for part in phrase.split())

    def _is_ambiguous(self, candidates: tuple[ShiftTargetCandidate, ...]) -> bool:
        if len(candidates) < 2:
            return False
        return candidates[0].score - candidates[1].score <= 0.04

    def _looks_like_shift_target_request(self, text: str) -> bool:
        normalized = f" {normalize_private_text(text)} "
        if not any(marker in normalized for marker in _SHIFT_MARKERS):
            return False
        if any(marker in normalized for marker in (" у меня ", " моя ", " мою ", " отмен", " я запис")):
            return False
        if any(marker in normalized for marker in (" запис", " запиш")):
            return True
        return any(marker in normalized for marker in (" к ", " ко ", " у ", " с ", " со ", " в ", " во "))
