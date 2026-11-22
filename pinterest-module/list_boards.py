"""List Pinterest boards available to the authorized account. Read-only."""
from __future__ import annotations

import httpx

from token_store import load_tokens

BOARDS_URL = "https://api.pinterest.com/v5/boards"


def main() -> int:
    tokens = load_tokens()
    access_token = tokens.get("access_token")
    if not access_token:
        raise RuntimeError("No access token found. Re-authorize at /auth/start.")
    response = httpx.get(
        BOARDS_URL,
        params={"page_size": 100},
        headers={"Authorization": "Bearer " + access_token},
        timeout=30,
    )
    response.raise_for_status()
    boards = response.json().get("items", [])
    if not boards:
        print("No boards returned.")
        return 0
    for board in boards:
        print(f"{board.get('id')}  |  {board.get('name')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
