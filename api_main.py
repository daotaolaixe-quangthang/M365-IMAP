from fastapi import FastAPI, HTTPException

import config
from api_schemas import OAuthLinkResponse, OAuthRefreshTokenRequest, OAuthRefreshTokenResponse
from auth_client import create_app
from oauth_session_store import (
    DEFAULT_SESSION_TTL_SECONDS,
    create_oauth_session,
    delete_oauth_session,
    get_oauth_session,
)
from oauth_utils import generate_oauth_value, resolve_code_and_state

REDIRECT_URI = "https://localhost:7598/"

app = FastAPI(title="M365 Outlook OAuth API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/outlook/oauth/link", response_model=OAuthLinkResponse)
def get_oauth_link():
    state = generate_oauth_value()
    oauth_session = create_oauth_session(
        state=state,
        redirect_uri=REDIRECT_URI,
        scopes=config.GraphScopes,
        ttl_seconds=DEFAULT_SESSION_TTL_SECONDS,
    )
    msal_app = create_app()
    auth_url = msal_app.get_authorization_request_url(
        config.GraphScopes,
        redirect_uri=REDIRECT_URI,
        state=state,
    )
    return OAuthLinkResponse(
        oauth_session=oauth_session.oauth_session,
        state=state,
        auth_url=auth_url,
        expires_in=DEFAULT_SESSION_TTL_SECONDS,
    )


@app.post("/api/outlook/oauth/refresh-token", response_model=OAuthRefreshTokenResponse)
def get_refresh_token(payload: OAuthRefreshTokenRequest):
    oauth_session = get_oauth_session(payload.oauth_session)
    if oauth_session is None:
        raise HTTPException(status_code=404, detail="OAuth session not found or expired")

    code, state = resolve_code_and_state(payload.redirect_url, payload.code, payload.state)
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")
    if state != oauth_session.state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    msal_app = create_app()
    token = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=oauth_session.scopes,
        redirect_uri=oauth_session.redirect_uri,
    )

    if "error" in token:
        raise HTTPException(
            status_code=400,
            detail={
                "error": token.get("error"),
                "error_description": token.get("error_description"),
                "correlation_id": token.get("correlation_id"),
            },
        )

    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=400,
            detail="Microsoft did not return a refresh token",
        )

    delete_oauth_session(payload.oauth_session)
    return OAuthRefreshTokenResponse(
        refresh_token=refresh_token,
        access_token=token.get("access_token"),
        expires_in=token.get("expires_in"),
        scope=token.get("scope"),
        token_type=token.get("token_type"),
    )
