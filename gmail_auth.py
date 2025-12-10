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

got_tokens = {}

class Handler(http.server.BaseHTTPRequestHandler):
    client_id = None
    client_secret = None
    redirect_uri = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        # Handle refresh token path
        if parsed.path == "/refresh" and "token" in qs:
            refresh_token = qs["token"][0]
            print(f"Refresh token received, exchanging for new access token...")
            try:
                tokens = self.refresh_access_token(refresh_token)
                got_tokens["tokens"] = tokens
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Token refresh successful! You can close this window.")
            except Exception as e:
                print(f"Error refreshing token: {e}")
                got_tokens["error"] = str(e)
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Error during token refresh. Check the console.")
        # Handle OAuth code exchange
        elif "code" in qs:
            code = qs["code"][0]
            print(f"Auth code received: {code}")
            print("Exchanging code for tokens...")
            try:
                tokens = self.exchange_code_for_tokens(code)
                got_tokens["tokens"] = tokens
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Authentication successful! You can close this window.")
            except Exception as e:
                print(f"Error exchanging code: {e}")
                got_tokens["error"] = str(e)
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Error during authentication. Check the console.")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No code or refresh token found.")

    def exchange_code_for_tokens(self, code: str):
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        req = urllib.request.Request(
            TOKEN_URL,
            data=urllib.parse.urlencode(data).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())

    def refresh_access_token(self, refresh_token: str):
        """Use a refresh token to get a new access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
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


def main():
    args = parse_args()

    redirect_uri = f"http://localhost:{args.port}/"

    # Configure Handler with client credentials
    Handler.client_id = args.client_id
    Handler.client_secret = args.client_secret
    Handler.redirect_uri = redirect_uri

    # Start local server to catch the redirect
    server = http.server.HTTPServer(("localhost", args.port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # If refresh token is provided, use the Handler to refresh the access token
    if args.refresh_token:
        print("Refreshing access token using refresh token...")
        refresh_url = f"{redirect_uri}refresh?token={args.refresh_token}"
        print(f"Opening browser to trigger refresh...")
        webbrowser.open(refresh_url)
        print(f"If it doesn't open, visit:\n{refresh_url}\n")
    else:
        # Otherwise, do the full OAuth flow
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

    print("Waiting for response...")
    while "tokens" not in got_tokens and "error" not in got_tokens:
        pass  # simple wait loop; Ctrl+C to abort

    server.shutdown()

    if "error" in got_tokens:
        print(f"\nError during token exchange: {got_tokens['error']}")
        import sys
        sys.exit(1)

    tokens = got_tokens["tokens"]
    print("\nTokens:")
    print(json.dumps(tokens, indent=2))

    if args.refresh_token:
        print("\nUpdate IMAP_TOKEN in your .env file with the new access_token.")
        print("Note: Refresh responses don't include a new refresh_token; keep using your existing one.")
    else:
        print("\nSave the refresh_token securely; use the access_token with imap_tools.xoauth2().")
        print("To refresh the access_token later, run:")
        print(f"  python3 gmail_auth.py --client-id {args.client_id} --client-secret YOUR_SECRET --refresh-token YOUR_REFRESH_TOKEN")

if __name__ == "__main__":
  main()
