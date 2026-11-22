"""Windows-only DPAPI storage and refresh for Pinterest OAuth tokens."""
from __future__ import annotations

import base64
import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Credentials and tokens remain outside the cloned repository.
ENV_FILE = Path(os.getenv("PINTEREST_ENV_FILE", r"C:\AgentAI\_shared\pinterest.env"))
TOKEN_PATH = Path(os.getenv("PINTEREST_TOKEN_FILE", r"C:\AgentAI\_shared\pinterest.tokens.json"))
TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes) -> tuple[DATA_BLOB, ctypes.Array[ctypes.c_char]]:
    buffer = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def _crypt(data: bytes, protect: bool) -> bytes:
    if os.name != "nt":
        raise RuntimeError("DPAPI token storage is supported only on Windows.")
    source, source_buffer = _blob(data)
    target = DATA_BLOB()
    crypt32 = ctypes.WinDLL("Crypt32.dll")
    kernel32 = ctypes.WinDLL("Kernel32.dll")
    operation = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    ok = operation(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target))
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel32.LocalFree(target.pbData)


def save_tokens(tokens: dict) -> None:
    encrypted = _crypt(json.dumps(tokens).encode("utf-8"), protect=True)
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps({"dpapi": base64.b64encode(encrypted).decode("ascii")}), encoding="utf-8")


def load_tokens() -> dict:
    if not TOKEN_PATH.exists():
        raise FileNotFoundError("Pinterest is not authorized yet. Open /auth/start first.")
    wrapper = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    decrypted = _crypt(base64.b64decode(wrapper["dpapi"]), protect=False)
    return json.loads(decrypted.decode("utf-8"))


def refresh_tokens(tokens: dict | None = None) -> dict:
    """Exchange the stored refresh token for a new access token and save it."""
    tokens = tokens or load_tokens()
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("No refresh token found. Re-authorize at /auth/start.")

    load_dotenv(ENV_FILE, override=True)
    client_id = os.getenv("PINTEREST_CLIENT_ID", "").strip()
    client_secret = os.getenv("PINTEREST_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError(f"Pinterest credentials are missing in {ENV_FILE}")

    response = httpx.post(
        TOKEN_URL,
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        auth=(client_id, client_secret),
        headers={"Accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    refreshed = {**tokens, **response.json()}
    save_tokens(refreshed)
    return refreshed
