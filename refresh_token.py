import sys
from pathlib import Path

from auth_client import create_app, get_token_config

# Set to False if you only want to refresh the token files without printing
# the access token (e.g. for periodic refresh jobs).
print_access_token = True

profile = sys.argv[1] if len(sys.argv) > 1 else "imap_smtp"
scopes, refresh_token_file, access_token_file = get_token_config(profile)
app = create_app()

refresh_path = Path(refresh_token_file)
if not refresh_path.exists():
    sys.exit(
        f"Refresh token file {refresh_token_file} not found. "
        f"Run get_token.py {profile} first."
    )

old_refresh_token = refresh_path.read_text().strip()

# Request a new access token (and usually a new refresh token).
token = app.acquire_token_by_refresh_token(old_refresh_token, scopes=scopes)

if "error" in token:
    print(token)
    sys.exit("Failed to get access token")

# Save the new refresh token if MSAL returned one; otherwise keep the old one.
new_refresh_token = token.get("refresh_token", old_refresh_token)
refresh_path.write_text(new_refresh_token)

with open(access_token_file, "w") as f:
    f.write(token["access_token"])

if print_access_token:
    # Printing the access token allows SMTP clients like msmtp to use this
    # script as password source (passwordeval).
    print(token["access_token"])