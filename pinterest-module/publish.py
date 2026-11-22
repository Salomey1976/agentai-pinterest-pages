"""Controlled command-line Pin publisher. Dry-run by default."""
from __future__ import annotations

import argparse
import json
import sys

import httpx

from token_store import load_tokens

CREATE_PIN_URL = "https://api.pinterest.com/v5/pins"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create one Pinterest Pin from an image URL.")
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--image-url", required=True, help="Public HTTPS URL of the image.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--link", required=True, help="Destination URL for the Pin.")
    parser.add_argument("--publish", action="store_true", help="Actually create the Pin. Without this, show the payload only.")
    return parser.parse_args()


def main() -> int:
    args = arguments()
    payload = {
        "board_id": args.board_id,
        "media_source": {"source_type": "image_url", "url": args.image_url},
        "title": args.title,
        "description": args.description,
        "link": args.link,
    }
    if not args.publish:
        print("DRY RUN — no Pin has been created. Review payload, then rerun with --publish.")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    tokens = load_tokens()
    access_token = tokens.get("access_token")
    if not access_token:
        raise RuntimeError("No access token found. Re-authorize at /auth/start.")
    response = httpx.post(
        CREATE_PIN_URL,
        json=payload,
        headers={"Authorization": "Bearer " + access_token, "Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    print(f"Pin created: {result.get('id', 'unknown id')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Publish failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
