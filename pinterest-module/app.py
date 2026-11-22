"""Local OAuth callback service for the private AgentAI Pinterest integration."""
from __future__ import annotations

import os
import secrets
from pathlib import Path
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from token_store import save_tokens

# Credentials stay outside the cloned repository. Override only with PINTEREST_ENV_FILE.
ENV_FILE = Path(os.getenv("PINTEREST_ENV_FILE", r"C:\AgentAI\_shared\.env"))
load_dotenv(ENV_FILE)

AUTHORIZE_URL = "https://www.pinterest.com/oauth/"
TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
PENDING_STATES: set[str] = set()

app = FastAPI(title="AgentAI Pinterest local module", docs_url=None, redoc_url=None)


def setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise HTTPException(status_code=500, detail=f"Missing {name} in {ENV_FILE}")
    return value


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "agentai-pinterest-local", "configuration_found": ENV_FILE.exists()}


@app.get("/auth/start")
async def auth_start() -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    PENDING_STATES.add(state)
    params = {
        "client_id": setting("PINTEREST_CLIENT_ID"),
        "redirect_uri": setting("PINTEREST_REDIRECT_URI"),
        "response_type": "code",
        "scope": setting("PINTEREST_SCOPES"),
        "state": state,
    }
    return RedirectResponse(f"{AUTHORIZE_URL}?{urlencode(params)}")


@app.get("/pinterest/callback", response_class=HTMLResponse)
async def auth_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None) -> str:
    if error:
        return f"<h1>Pinterest authorization was not completed</h1><p>{error}</p>"
    if not code or not state or state not in PENDING_STATES:
        raise HTTPException(status_code=400, detail="Invalid or expired authorization state. Start again at /auth/start.")
    PENDING_STATES.remove(state)

    client_id = setting("PINTEREST_CLIENT_ID")
    client_secret = setting("PINTEREST_CLIENT_SECRET")
    redirect_uri = setting("PINTEREST_REDIRECT_URI")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            TOKEN_URL,
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
            auth=(client_id, client_secret),
            headers={"Accept": "application/json"},
        )
    if response.is_error:
        raise HTTPException(status_code=502, detail="Pinterest token exchange failed. Check the redirect URI and app credentials.")
    save_tokens(response.json())
    return "<h1>Pinterest connected</h1><p>Tokens were encrypted with Windows DPAPI for this Windows account. You may close this page.</p>"
