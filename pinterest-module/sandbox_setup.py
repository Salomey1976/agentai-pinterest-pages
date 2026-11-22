"""Store a Pinterest Sandbox token locally and obtain a Sandbox-only test board."""
from __future__ import annotations

import argparse
import getpass
import sys

import httpx

from token_store import load_sandbox_tokens, save_sandbox_token

SANDBOX_BOARDS_URL = "https://api-sandbox.pinterest.com/v5/boards"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Configure a local Pinterest Sandbox test board.")
    parser.add_argument("--board-name", default="AgentAI Sandbox Test")
    parser.add_argument("--replace-token", action="store_true", help="Prompt for and replace the encrypted Sandbox token.")
    return parser.parse_args()


def access_token(replace: bool) -> str:
    if not replace:
        try:
            token = load_sandbox_tokens().get("access_token", "").strip()
            if token:
                return token
        except FileNotFoundError:
            pass
    token = getpass.getpass("Paste the Pinterest Sandbox token (input is hidden): ").strip()
    save_sandbox_token(token)
    return token


def main() -> int:
    args = arguments()
    token = access_token(args.replace_token)
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    listed = httpx.get(SANDBOX_BOARDS_URL, headers=headers, timeout=30)
    if listed.is_error:
        raise RuntimeError(f"Pinterest Sandbox API {listed.status_code}: {listed.text[:1000]}")
    for board in listed.json().get("items", []):
        if board.get("name") == args.board_name:
            print("Sandbox token is encrypted with Windows DPAPI.")
            print(f"Sandbox board ready: {board.get('id', 'unknown id')}  |  {args.board_name}")
            return 0

    response = httpx.post(
        SANDBOX_BOARDS_URL,
        json={"name": args.board_name, "privacy": "PUBLIC"},
        headers=headers,
        timeout=30,
    )
    if response.is_error:
        raise RuntimeError(f"Pinterest Sandbox API {response.status_code}: {response.text[:1000]}")
    board = response.json()
    print("Sandbox token is encrypted with Windows DPAPI.")
    print(f"Sandbox board ready: {board.get('id', 'unknown id')}  |  {board.get('name', args.board_name)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Sandbox setup failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
