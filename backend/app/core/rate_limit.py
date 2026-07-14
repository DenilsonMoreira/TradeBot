from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from typing import Callable


@dataclass
class _AttemptState:
    attempts: deque[float] = field(default_factory=deque)
    locked_until: float = 0.0


class LoginRateLimiter:
    """Limita tentativas por chave opaca em uma única instância da API."""

    def __init__(
        self,
        max_attempts: int,
        window_seconds: int,
        lockout_seconds: int,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._clock = clock
        self._states: dict[str, _AttemptState] = {}
        self._lock = Lock()

    def retry_after(self, key: str) -> int:
        now = self._clock()
        with self._lock:
            state = self._states.get(key)
            if state is None:
                return 0
            if state.locked_until > now:
                return max(1, int(state.locked_until - now + 0.999))
            self._prune(state, now)
            if not state.attempts:
                self._states.pop(key, None)
            return 0

    def register_failure(self, key: str) -> int:
        now = self._clock()
        with self._lock:
            state = self._states.setdefault(key, _AttemptState())
            self._prune(state, now)
            state.attempts.append(now)
            if len(state.attempts) >= self.max_attempts:
                state.locked_until = now + self.lockout_seconds
                return self.lockout_seconds
            return 0

    def register_success(self, key: str) -> None:
        with self._lock:
            self._states.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._states.clear()

    def _prune(self, state: _AttemptState, now: float) -> None:
        cutoff = now - self.window_seconds
        while state.attempts and state.attempts[0] <= cutoff:
            state.attempts.popleft()

