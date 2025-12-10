#!/usr/bin/env python3
import argparse
import urllib.parse
import webbrowser

SCOPE = "https://mail.google.com/"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Gmail OAuth client. Triggers authentication or token refresh. "
                    "Requires gmail_auth_server.py to be running first."
    )
    parser.add_argument("--client-id", required=True, help="OAuth client ID")
    parser.add_argument(
        "--refresh-token",
        help="Existing refresh token to use for getting a new access token",
    )
    parser.add_argument(
        "--server",
        default="http://localhost:8080",
        help="Server address where gmail_auth_server.py is running (default: http://localhost:8080)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Ensure server address ends with /
    server_address = args.server if args.server.endswith('/') else args.server + '/'

    # If refresh token is provided, trigger refresh
    if args.refresh_token:
        print("Triggering token refresh...")
        refresh_url = f"{server_address}refresh?token={args.refresh_token}"
        print(f"Opening browser to: {refresh_url}")
        webbrowser.open(refresh_url)
        print("\nCheck the gmail_auth_server.py terminal for the new tokens.")
    else:
        # Otherwise, trigger the full OAuth flow
        params = {
            "client_id": args.client_id,
            "redirect_uri": server_address,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }
        auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
        print("Triggering OAuth authentication...")
        print(f"Opening browser to: {auth_url}")
        webbrowser.open(auth_url)
        print("\nComplete the authentication in your browser.")
        print("Check the gmail_auth_server.py terminal for the tokens.")


if __name__ == "__main__":
    main()
