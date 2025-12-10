#!/usr/bin/env python3
import argparse
import base64
import http.server
import json
import urllib.parse
import urllib.request

SCOPE = "https://mail.google.com/"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"


class Handler(http.server.BaseHTTPRequestHandler):
    client_id = None
    client_secret = None
    redirect_uri = None
    whitelist = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        # Handle refresh token path
        if parsed.path == "/refresh" and "token" in qs:
            refresh_token = qs["token"][0]
            print(f"Refresh token received, exchanging for new access token...")
            try:
                tokens = self.refresh_access_token(refresh_token)

                # Check whitelist if configured
                if self.whitelist is not None:
                    email = self.get_user_email(tokens["access_token"])
                    print(f"Email: {email}")
                    if not self.is_email_allowed(email):
                        print(f"REJECTED: Email {email} is not in the whitelist.")
                        self.send_response(403)
                        self.end_headers()
                        self.wfile.write(f"Access denied: {email} is not authorized.".encode())
                        return
                    print(f"ACCEPTED: Email {email} is whitelisted.")

                print("\nNew tokens:")
                print(json.dumps(tokens, indent=2))
                print("\nUpdate IMAP_TOKEN in your .env file with the new access_token.")
                print("Note: Refresh responses don't include a new refresh_token; keep using your existing one.")
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Token refresh successful! You can close this window.")
            except Exception as e:
                print(f"Error refreshing token: {e}")
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

                # Check whitelist if configured
                if self.whitelist is not None:
                    email = self.get_user_email(tokens["access_token"])
                    print(f"Email: {email}")
                    if not self.is_email_allowed(email):
                        print(f"REJECTED: Email {email} is not in the whitelist.")
                        self.send_response(403)
                        self.end_headers()
                        self.wfile.write(f"Access denied: {email} is not authorized. Send an email to laurent@vivier.eu to be added.".encode())
                        return
                    print(f"ACCEPTED: Email {email} is whitelisted.")

                print("\nTokens:")
                print(json.dumps(tokens, indent=2))
                print("\nSave the refresh_token securely; use the access_token with imap_tools.xoauth2().")
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Authentication successful! You can close this window.")
            except Exception as e:
                print(f"Error exchanging code: {e}")
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

    def get_user_email(self, access_token: str):
        """Get the user's email address using the access token."""
        req = urllib.request.Request(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        with urllib.request.urlopen(req) as resp:
            userinfo = json.loads(resp.read().decode())
            return userinfo.get("email")

    def is_email_allowed(self, email: str):
        """Check if the email is in the whitelist."""
        if self.whitelist is None:
            return True  # No whitelist means all emails are allowed
        return email in self.whitelist

    def log_message(self, *args, **kwargs):
        pass  # silence server logs


def parse_args():
    parser = argparse.ArgumentParser(
        description="Gmail OAuth token server. Start this server, then use gmail_auth_client.py to request tokens."
    )
    parser.add_argument("--client-id", required=True, help="OAuth client ID")
    parser.add_argument("--client-secret", required=True, help="OAuth client secret")
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Local port to listen for the OAuth redirect (default: 8080)",
    )
    parser.add_argument(
        "--whitelist",
        help="Comma-separated list of allowed email addresses (e.g., user1@example.com,user2@example.com). If not specified, all emails are allowed.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    redirect_uri = f"http://localhost:{args.port}/"

    # Parse whitelist if provided
    whitelist = None
    if args.whitelist:
        whitelist = set(email.strip() for email in args.whitelist.split(","))
        print(f"Email whitelist enabled: {', '.join(sorted(whitelist))}")

    # Configure Handler with client credentials
    Handler.client_id = args.client_id
    Handler.client_secret = args.client_secret
    Handler.redirect_uri = redirect_uri
    Handler.whitelist = whitelist

    # Start local server
    server = http.server.HTTPServer(("localhost", args.port), Handler)
    print(f"Gmail OAuth server started on {redirect_uri}")
    print(f"Waiting for OAuth callbacks...")
    print(f"Use gmail_auth_client.py to trigger authentication or token refresh.")
    print(f"Press Ctrl+C to stop the server.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


if __name__ == "__main__":
    main()
