from msal import ConfidentialClientApplication, PublicClientApplication, SerializableTokenCache

import config


def create_app():
    cache = SerializableTokenCache()
    if config.ClientSecret:
        return ConfidentialClientApplication(
            client_id=config.ClientId,
            client_credential=config.ClientSecret,
            token_cache=cache,
            authority=config.Authority,
        )

    return PublicClientApplication(
        client_id=config.ClientId,
        token_cache=cache,
        authority=config.Authority,
    )


def get_token_config(profile: str):
    normalized = (profile or "imap_smtp").strip().lower().replace("-", "_")

    if normalized in {"imap", "smtp", "imap_smtp"}:
        return (
            config.ImapSmtpScopes,
            config.ImapSmtpRefreshTokenFileName,
            config.ImapSmtpAccessTokenFileName,
        )

    if normalized in {"graph", "msgraph", "microsoft_graph"}:
        return (
            config.GraphScopes,
            config.GraphRefreshTokenFileName,
            config.GraphAccessTokenFileName,
        )

    raise SystemExit("Unknown token profile. Use 'imap_smtp' or 'graph'.")
