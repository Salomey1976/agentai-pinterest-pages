# AgentAI Pinterest module

Local Windows service for a private Pinterest integration. It is deliberately separate from GitHub Pages: Pages hosts the public description and privacy policy only.

## What it does
- starts Pinterest OAuth authorization;
- receives the OAuth callback;
- exchanges the code for access and refresh tokens;
- stores tokens with Windows DPAPI for the current Windows account;
- publishes Pins from a local command line.

## Security
Never commit `.env`, client secrets, access tokens, refresh tokens or logs. The redirect URI must exactly match the value registered in Pinterest Developers: `http://localhost:8080/pinterest/callback`.

## Windows quick start
```powershell
cd pinterest-module
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Fill PINTEREST_CLIENT_ID and PINTEREST_CLIENT_SECRET.
uvicorn app:app --host 127.0.0.1 --port 8080
```

Open `http://localhost:8080/auth/start` in the same browser that will authorize Pinterest.

## Publishing
After successful authorization:
```powershell
python publish.py --board-id YOUR_BOARD_ID --image-url https://example.com/image.jpg --title "Title" --description "Description" --link https://example.com
```

Run this only on the controlled AgentAI computer. The integration is for the owner’s Pinterest account and must comply with Pinterest policies.
