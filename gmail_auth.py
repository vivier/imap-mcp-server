#!/usr/bin/env python3
import argparse
import http.server
import json
import threading
import urllib.parse
import urllib.request
import webbrowser

SCOPE = "https://mail.google.com/"
TOKEN_URL = "https://oauth2.googleapis.com/token"

got_code = {}

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if "code" in qs:
            got_code["code"] = qs["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"You can close this window.")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No code found.")

    def log_message(self, *args, **kwargs):
        pass  # silence server logs


def parse_args():
    parser = argparse.ArgumentParser(
        description="Get Gmail OAuth tokens. Use without --refresh-token for initial setup, "
                    "or with --refresh-token to refresh an existing token."
    )
    parser.add_argument("--client-id", required=True, help="OAuth client ID")
    parser.add_argument("--client-secret", required=True, help="OAuth client secret")
    parser.add_argument(
        "--refresh-token",
        help="Existing refresh token to use for getting a new access token",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Local port to listen for the OAuth redirect (default: 8080)",
    )
    return parser.parse_args()


def exchange_code_for_tokens(code: str, client_id: str, client_secret: str, redirect_uri: str):
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    req = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def refresh_access_token(refresh_token: str, client_id: str, client_secret: str):
    """Use a refresh token to get a new access token."""
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    req = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main():
    args = parse_args()

    # If refresh token is provided, just refresh the access token
    if args.refresh_token:
        print("Refreshing access token using refresh token...")
        try:
            tokens = refresh_access_token(args.refresh_token, args.client_id, args.client_secret)
            print("\nNew tokens:")
            print(json.dumps(tokens, indent=2))
            print("\nUpdate IMAP_TOKEN in your .env file with the new access_token.")
            print("Note: Refresh responses don't include a new refresh_token; keep using your existing one.")
        except Exception as e:
            print(f"Error refreshing token: {e}")
            import sys
            sys.exit(1)
        return

    # Otherwise, do the full OAuth flow
    redirect_uri = f"http://localhost:{args.port}/"

    # Start local server to catch the redirect
    server = http.server.HTTPServer(("localhost", args.port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    params = {
        "client_id": args.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    print("Opening browser for consent...")
    webbrowser.open(auth_url)
    print(f"If it doesn't open, visit:\n{auth_url}\n")

    print("Waiting for OAuth redirect with code...")
    while "code" not in got_code:
        pass  # simple wait loop; Ctrl+C to abort

    server.shutdown()
    code = got_code["code"]
    print(f"Auth code received: {code}")

    print("Exchanging code for tokens...")
    tokens = exchange_code_for_tokens(code, args.client_id, args.client_secret, redirect_uri)
    print("\nTokens:")
    print(json.dumps(tokens, indent=2))

    print("\nSave the refresh_token securely; use the access_token with imap_tools.xoauth2().")
    print("To refresh the access_token later, run:")
    print(f"  python3 gmail_auth.py --client-id {args.client_id} --client-secret YOUR_SECRET --refresh-token YOUR_REFRESH_TOKEN")

if __name__ == "__main__":
  main()
