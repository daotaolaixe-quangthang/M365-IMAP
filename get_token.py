import argparse
import http.server
import os
import ssl
import sys
import threading
import urllib.parse
from pathlib import Path

from auth_client import create_app, get_token_config

redirect_uri = "https://localhost:7598/"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Get OAuth tokens for Microsoft 365 profiles."
    )
    parser.add_argument(
        "profile",
        nargs="?",
        default="imap_smtp",
        help="Token profile to use: imap_smtp or graph.",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Do not start the local HTTPS callback server. Paste the final redirect URL manually.",
    )
    return parser.parse_args()


def extract_authorization_code(value: str) -> str:
    value = value.strip()
    if not value:
        return ""

    parsed_url = urllib.parse.urlparse(value)
    parsed_query = urllib.parse.parse_qs(parsed_url.query or parsed_url.fragment)
    code = next(iter(parsed_query.get("code", [""])), "")
    if code:
        return code

    if value.startswith("code="):
        parsed_query = urllib.parse.parse_qs(value)
        code = next(iter(parsed_query.get("code", [""])), "")
        if code:
            return code

    marker = "code="
    if marker in value:
        start = value.find(marker) + len(marker)
        end = value.find("&", start)
        code = value[start:] if end == -1 else value[start:end]
        return urllib.parse.unquote(code)

    return value


def read_code_manually() -> str:
    print("Manual mode is active.")
    print("After login, the browser may show a localhost certificate or connection error.")
    print("Copy the full URL from the browser address bar and paste it here.")
    print("You can also paste only the code value after code=.")

    while True:
        pasted = input("Paste final redirect URL or code: ").strip()
        code = extract_authorization_code(pasted)
        if code:
            return code
        print("No authorization code found. Please paste the full redirect URL or code value.")


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        parsed_query = urllib.parse.parse_qs(parsed_url.query)
        global code
        code = next(iter(parsed_query.get("code", [""])), "")

        response_body = b"Success. You can return to the terminal.\r\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", len(response_body))
        self.end_headers()
        self.wfile.write(response_body)

        global httpd
        t = threading.Thread(target=httpd.shutdown)
        t.start()


def read_code_from_callback_server() -> str:
    global httpd
    server_address = ("", 7598)
    httpd = http.server.HTTPServer(server_address, Handler)
    root = Path(__file__).parent
    keyf, certf = root / "server.key", root / "server.cert"
    assert keyf.exists() and certf.exists(), "server.key / server.cert not found"
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certf, keyf)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    print("Waiting for the login redirect on https://localhost:7598/ ...")
    httpd.serve_forever()
    return code


def main() -> None:
    args = parse_args()
    scopes, refresh_token_file, access_token_file = get_token_config(args.profile)
    app = create_app()
    url = app.get_authorization_request_url(scopes, redirect_uri=redirect_uri)

    print("Copy the following URL and open it in the browser you want to use:")
    print(url)

    global code
    code = ""
    if args.manual or os.getenv("SSH_CONNECTION"):
        code = read_code_manually()
    else:
        code = read_code_from_callback_server()
        if not code:
            code = read_code_manually()

    token = app.acquire_token_by_authorization_code(
        code,
        scopes=scopes,
        redirect_uri=redirect_uri,
    )

    if "error" in token:
        print(token)
        sys.exit("Failed to get access token")

    with open(refresh_token_file, "w") as f:
        print(f"Refresh token acquired, writing to file {refresh_token_file}")
        f.write(token["refresh_token"])

    with open(access_token_file, "w") as f:
        print(f"Access token acquired, writing to file {access_token_file}")
        f.write(token["access_token"])


code = ""
httpd = None

if __name__ == "__main__":
    main()
