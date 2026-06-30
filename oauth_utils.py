import secrets
import urllib.parse
from typing import Optional, Tuple


def generate_oauth_value() -> str:
    return secrets.token_urlsafe(32)


def parse_redirect_url(redirect_url: str) -> Tuple[str, str]:
    value = (redirect_url or "").strip()
    if not value:
        return "", ""

    parsed_url = urllib.parse.urlparse(value)
    query = parsed_url.query or parsed_url.fragment
    parsed_query = urllib.parse.parse_qs(query)

    if not parsed_query and value.startswith("code="):
        parsed_query = urllib.parse.parse_qs(value)

    code = next(iter(parsed_query.get("code", [""])), "")
    state = next(iter(parsed_query.get("state", [""])), "")
    return urllib.parse.unquote(code), urllib.parse.unquote(state)


def resolve_code_and_state(
    redirect_url: Optional[str],
    code: Optional[str],
    state: Optional[str],
) -> Tuple[str, str]:
    parsed_code, parsed_state = parse_redirect_url(redirect_url or "")
    return (code or parsed_code or "").strip(), (state or parsed_state or "").strip()
