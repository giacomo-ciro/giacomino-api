# System Architecture

Minimal overview of how the **Giacomino API** is hosted, tunneled, secured, and connected to the website.

---

## 1. Components

- **Frontend**: [`giacomociro.com`](https://giacomociro.com) hosted on **Cloudflare Pages**.
- **Backend API**: FastAPI running locally on a **Raspberry Pi 5**.
- **Tunnel**: **Cloudflare Tunnel** (`cloudflared`) exposing local port `5001` to `giacomino.giacomociro.com`.
- **Security**: **Cloudflare Access (Zero Trust)** locking the entire `giacomino.giacomociro.com` domain.

---

## 2. Request Flows

```
[ Visitor at giacomociro.com ]
             │
             │ POST /giacomino/chat (Same-origin, no CORS)
             ▼
[ Cloudflare Pages Function ]
             │ Injects Cloudflare Access Service Token
             ▼
[ Cloudflare Access Wall ] ◄─────── [ You via Browser SSO ]
             │                      (https://giacomino.giacomociro.com -> Dashboard)
             │ Validates token or SSO session
             ▼
[ Cloudflare Tunnel (cloudflared) ]
             ▼
[ Raspberry Pi 5 (FastAPI / Gunicorn on :5001) ]
```

---

## 3. Cloudflare Access Rules

1. **User Policy (For You)**:
   - Login via Google/GitHub SSO.
   - Grants full browser access to the dashboard at `https://giacomino.giacomociro.com/`.

2. **Service Token Policy (For the Website)**:
   - Create a Cloudflare Access **Service Token** (`CF-Access-Client-Id` and `CF-Access-Client-Secret`).
   - Add a Non-Identity Policy allowing requests bearing this Service Token.

---

## 4. Implementation Details

### A. Raspberry Pi 5 Service (`systemd`)
Managed as a `systemd` service running Gunicorn with Uvicorn workers:

```ini
[Unit]
Description=Giacomino FastAPI Backend
After=network.target

[Service]
User=gciro
WorkingDirectory=/home/gciro/giacomino-api
ExecStart=/home/gciro/giacomino-api/.venv/bin/gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:5001
Restart=always

[Install]
WantedBy=multi-user.target
```

### B. Cloudflare Pages Proxy (`functions/giacomino/chat.ts`)
Placed in your website repo to proxy chat requests without exposing secrets:

```typescript
export async function onRequestPost(context: any) {
  const body = await context.request.json();

  const response = await fetch("https://giacomino.giacomociro.com/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "CF-Access-Client-Id": context.env.CF_ACCESS_CLIENT_ID,
      "CF-Access-Client-Secret": context.env.CF_ACCESS_CLIENT_SECRET,
    },
    body: JSON.stringify(body),
  });

  return new Response(response.body, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}
```
