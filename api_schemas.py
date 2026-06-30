from typing import Optional

from pydantic import BaseModel, root_validator


class OAuthLinkResponse(BaseModel):
    oauth_session: str
    state: str
    auth_url: str
    expires_in: int


class OAuthRefreshTokenRequest(BaseModel):
    oauth_session: str
    redirect_url: Optional[str] = None
    code: Optional[str] = None
    state: Optional[str] = None

    @root_validator(skip_on_failure=True)
    def validate_code_source(cls, values):
        redirect_url = values.get("redirect_url")
        code = values.get("code")
        state = values.get("state")
        if redirect_url or (code and state):
            return values
        raise ValueError("Provide redirect_url or both code and state")


class OAuthRefreshTokenResponse(BaseModel):
    refresh_token: str
    access_token: Optional[str] = None
    expires_in: Optional[int] = None
    scope: Optional[str] = None
    token_type: Optional[str] = None
