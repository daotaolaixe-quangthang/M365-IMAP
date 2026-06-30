import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from oauth_utils import generate_oauth_value


DEFAULT_SESSION_TTL_SECONDS = 600


@dataclass(frozen=True)
class OAuthSession:
    oauth_session: str
    state: str
    redirect_uri: str
    scopes: List[str]
    expires_at: float


_sessions: Dict[str, OAuthSession] = {}
_lock = threading.Lock()


def cleanup_expired_sessions() -> None:
    now = time.time()
    with _lock:
        expired = [key for key, session in _sessions.items() if session.expires_at <= now]
        for key in expired:
            _sessions.pop(key, None)


def create_oauth_session(
    state: str,
    redirect_uri: str,
    scopes: List[str],
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
) -> OAuthSession:
    cleanup_expired_sessions()
    oauth_session = generate_oauth_value()
    session = OAuthSession(
        oauth_session=oauth_session,
        state=state,
        redirect_uri=redirect_uri,
        scopes=list(scopes),
        expires_at=time.time() + ttl_seconds,
    )
    with _lock:
        _sessions[oauth_session] = session
    return session


def get_oauth_session(oauth_session: str) -> Optional[OAuthSession]:
    cleanup_expired_sessions()
    with _lock:
        return _sessions.get(oauth_session)


def delete_oauth_session(oauth_session: str) -> None:
    with _lock:
        _sessions.pop(oauth_session, None)
