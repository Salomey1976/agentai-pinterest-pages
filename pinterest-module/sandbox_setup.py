"""Store a Pinterest Sandbox token locally and create a Sandbox-only test board."""
from __future__ import annotations

import argparse
import getpass
import sys

import httpx

from token_store import save_sandbox_token

SANDBOX_BOARDS_URL = "https://api-sandbox.pinterest.com/v5/boards"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Configure a local Pinterest Sandbox test board.")
    parser.add_argument("--board-name", default="AgentAI Sandbox Test")
    return parser.parse_args()


def main() -> int:
    args = arguments()
    token = getpass.getpass("Paste the Pinterest Sandbox token (input is hidden): ").strip()
    save_sandbox_token(token)

    response = httpx.post(
        SANDBOX_BOARDS_URL,
        json={"name": args.board_name, "description": "Private test board for the AgentAI Pinterest integration."},
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        timeout=30,
    )
    if response.is_error:
        raise RuntimeError(f"Pinterest Sandbox API {response.status_code}: {response.text[:1000]}")
    board = response.json()
    print("Sandbox token encrypted with Windows DPAPI.")
    print(f"Sandbox board created: {board.get('id', 'unknown id')}  |  {board.get('name', args.board_name)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Sandbox setup failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
