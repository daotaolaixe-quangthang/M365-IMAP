import sys
from pathlib import Path

import requests

import config
from auth_client import create_app

GRAPH_MESSAGES_URL = "https://graph.microsoft.com/v1.0/me/messages"


def acquire_graph_access_token() -> str:
    refresh_path = Path(config.GraphRefreshTokenFileName)
    if not refresh_path.exists():
        sys.exit(
            f"Refresh token file {config.GraphRefreshTokenFileName} not found. "
            "Run python get_token.py graph first."
        )

    refresh_token = refresh_path.read_text().strip()
    token = create_app().acquire_token_by_refresh_token(
        refresh_token,
        scopes=config.GraphScopes,
    )

    if "error" in token:
        print(token)
        sys.exit("Failed to get Microsoft Graph access token")

    refresh_path.write_text(token.get("refresh_token", refresh_token))
    Path(config.GraphAccessTokenFileName).write_text(token["access_token"])
    return token["access_token"]


def sender_text(message: dict) -> str:
    email_address = message.get("from", {}).get("emailAddress", {})
    name = email_address.get("name", "")
    address = email_address.get("address", "")

    if name and address:
        return f"{name} <{address}>"
    return address or name or "(unknown sender)"


def show_recent_messages(limit: int = 15) -> None:
    access_token = acquire_graph_access_token()
    response = requests.get(
        GRAPH_MESSAGES_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "$top": str(limit),
            "$select": "receivedDateTime,from,subject,bodyPreview,webLink",
            "$orderby": "receivedDateTime desc",
        },
        timeout=30,
    )

    if not response.ok:
        print(response.status_code)
        print(response.text)
        sys.exit("Microsoft Graph request failed")

    messages = response.json().get("value", [])
    if not messages:
        print("No messages found.")
        return

    for index, message in enumerate(messages, start=1):
        print("-" * 60)
        print(f"#{index}")
        print(f"Date: {message.get('receivedDateTime', '')}")
        print(f"From: {sender_text(message)}")
        print(f"Subject: {message.get('subject') or '(no subject)'}")
        preview = (message.get("bodyPreview") or "").replace("\r", " ").replace("\n", " ")
        print(f"Preview: {preview[:300]}")
        if message.get("webLink"):
            print(f"Link: {message['webLink']}")


def main() -> None:
    limit = 15
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            sys.exit("Usage: python graph_demo.py [message_limit]")

    show_recent_messages(limit)


if __name__ == "__main__":
    main()
