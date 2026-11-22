"""Process a local Google Drive queue of Pinterest image Pins.

Dry-run is the default. A Pin is created only when --publish is supplied.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from token_store import load_sandbox_tokens, load_tokens, refresh_tokens

CREATE_PIN_URL = "https://api.pinterest.com/v5/pins"\nSANDBOX_PIN_URL = "https://api-sandbox.pinterest.com/v5/pins"
QUEUE_ROOT = Path(r"G:\Мой диск\Pinterest")
IMAGE_DIR = QUEUE_ROOT / "Изображения"
QUEUE_DIR = QUEUE_ROOT / "Очередь"
PUBLISHED_DIR = QUEUE_ROOT / "Опубликовано"
ERROR_DIR = QUEUE_ROOT / "Ошибки"
ALLOWED_TYPES = {"image/jpeg", "image/png"}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate or publish jobs from the Pinterest Drive queue.")
    parser.add_argument("--job", help="Job JSON filename in the Queue folder. Omit to process every JSON job.")
    parser.add_argument("--publish", action="store_true", help="Actually create Pins and move completed jobs.")\n    parser.add_argument("--sandbox", action="store_true", help="Use Pinterest Sandbox only; never production.")\n    parser.add_argument("--board-id", help="Override the job board ID, useful for a Sandbox test board.")
    return parser.parse_args()


def safe_child(folder: Path, name: str) -> Path:
    candidate = (folder / name).resolve()
    if candidate.parent != folder.resolve():
        raise ValueError("File name must not contain a path.")
    return candidate


def job_files(selected: str | None) -> list[Path]:
    if selected:
        path = safe_child(QUEUE_DIR, selected)
        if path.suffix.lower() != ".json":
            raise ValueError("--job must name a .json file.")
        return [path]
    return sorted(QUEUE_DIR.glob("*.json"))


def load_job(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Job file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    required = ("board_id", "image", "title", "description", "link")
    missing = [key for key in required if not isinstance(data.get(key), str) or not data[key].strip()]
    if missing:
        raise ValueError("Missing required text fields: " + ", ".join(missing))
    if len(data["title"]) > 100:
        raise ValueError("title must be 100 characters or fewer.")
    if len(data["description"]) > 800:
        raise ValueError("description must be 800 characters or fewer.")
    if data.get("alt_text") is not None and (not isinstance(data["alt_text"], str) or len(data["alt_text"]) > 500):
        raise ValueError("alt_text must be text of 500 characters or fewer.")
    return data


def build_payload(job: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    image_path = safe_child(IMAGE_DIR, job["image"])
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found in Images: {image_path.name}")

    content_type, _ = mimetypes.guess_type(image_path.name)
    if content_type not in ALLOWED_TYPES:
        raise ValueError("Only JPEG and PNG images are supported.")
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    payload: dict[str, Any] = {
        "board_id": job["board_id"].strip(),
        "title": job["title"].strip(),
        "description": job["description"].strip(),
        "link": job["link"].strip(),
        "media_source": {
            "source_type": "image_base64",
            "content_type": content_type,
            "data": encoded,
        },
    }
    if job.get("alt_text"):
        payload["alt_text"] = job["alt_text"].strip()
    return payload, image_path


def report_payload(payload: dict[str, Any], image_path: Path) -> dict[str, Any]:
    copy = dict(payload)
    copy["media_source"] = dict(payload["media_source"])
    copy["media_source"]["data"] = f"<base64: {image_path.name}, {image_path.stat().st_size} bytes>"
    return copy


def archive(path: Path, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / path.name
    if target.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = folder / f"{path.stem}-{timestamp}{path.suffix}"
    return Path(shutil.move(str(path), str(target)))


def publish(payload: dict[str, Any], sandbox: bool = False) -> dict[str, Any]:
    tokens = load_sandbox_tokens() if sandbox else load_tokens()
    endpoint = SANDBOX_PIN_URL if sandbox else CREATE_PIN_URL

    def send(current: dict) -> httpx.Response:
        access_token = current.get("access_token")
        if not access_token:
            raise RuntimeError("No access token found. Authorize the selected Pinterest environment first.")
        return httpx.post(
            endpoint,
            json=payload,
            headers={"Authorization": "Bearer " + access_token, "Content-Type": "application/json"},
            timeout=60,
        )

    response = send(tokens)
    if not sandbox and response.status_code == 401:
        tokens = refresh_tokens(tokens)
        response = send(tokens)
    if response.is_error:
        detail = response.text[:1000].replace("\n", " ")
        environment = "Sandbox" if sandbox else "production"
        raise RuntimeError(f"Pinterest {environment} API {response.status_code}: {detail}")
    return response.json()


def main() -> int:
    args = arguments()
    for folder in (IMAGE_DIR, QUEUE_DIR, PUBLISHED_DIR, ERROR_DIR):
        folder.mkdir(parents=True, exist_ok=True)

    files = job_files(args.job)
    if not files:
        print("No .json jobs found in Queue.")
        return 0

    failures = 0
    for job_path in files:
        try:
            job = load_job(job_path)
            payload, image_path = build_payload(job)
            if not args.publish:
                print(f"DRY RUN — {job_path.name}; no Pin has been created.")
                print(json.dumps(report_payload(payload, image_path), ensure_ascii=False, indent=2))
                continue

            result = publish(payload, sandbox=args.sandbox)
            archive(job_path, PUBLISHED_DIR)
            archive(image_path, PUBLISHED_DIR)
            receipt = PUBLISHED_DIR / f"{job_path.stem}.result.json"
            receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            environment = "Sandbox" if args.sandbox else "production"\n            print(f"Pin created in {environment}: {result.get('id', 'unknown id')}")
        except Exception as exc:
            failures += 1
            print(f"Job failed ({job_path.name}): {exc}", file=sys.stderr)
            if args.publish and job_path.exists():
                archive(job_path, ERROR_DIR)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
