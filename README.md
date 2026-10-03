# EscrowEase ⚖️

**Freelance escrow with an AI referee — built for the PayPal AI Hackathon.**

Hiring a freelancer shouldn't require blind trust. With EscrowEase:

1. The **client** creates a deal and funds escrow — PayPal **authorizes** (holds) the amount, without charging it yet.
2. The **freelancer** submits the deliverable.
3. An **AI referee** compares the work against the brief and issues a verdict: `APPROVE` or `REQUEST_CHANGES`, with a confidence score and reasons.
4. On approval, the client **releases** payment — PayPal **captures** the authorization and the freelancer gets paid. If things go wrong, the client **refunds** — PayPal **voids** the authorization and the money goes back.

Every money movement is a real PayPal **sandbox** REST API call. No mocks.

## Architecture

```
┌──────────────┐      ┌──────────────────────────┐      ┌─────────────────────┐
│   Browser    │◄────►│  Flask (backend/app.py)  │◄────►│  SQLite (deals,      │
│  templates/  │      │                          │      │  deliverables,       │
│  static/     │      │  ┌─────────────────────┐ │      │  verdicts)           │
└──────────────┘      │  │ paypal_client.py    │─┼──────┼─► api-m.sandbox.     │
                      │  │  OAuth2 → Orders    │ │      │   paypal.com         │
                      │  │  → Authorize →      │ │      └─────────────────────┘
                      │  │  Capture / Void     │ │
                      │  └─────────────────────┘ │      ┌─────────────────────┐
                      │  ┌─────────────────────┐ │      │  AI referee          │
                      │  │ ai_referee.py       │─┼──────┼─► text.pollinations  │
                      │  │  judge_deliverable  │ │      │   .ai (free, no key) │
                      │  └─────────────────────┘ │      │  or OpenAI-compatible│
                      │                          │      │  endpoint via env     │
                      └──────────────────────────┘      └─────────────────────┘
```

Deal state machine:

```
DRAFT → FUNDED → DELIVERED → APPROVED ─→ RELEASED (capture)
   │        │          │          │
   │        │          └→ CHANGES_REQUESTED → (resubmit) → DELIVERED
   │        └→ REFUNDED (void)   └→ REFUNDED (void)
   └ (cancel on PayPal → stays DRAFT)
```

## Setup

```bash
cd escrowease
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your sandbox credentials (see below)
python -m backend.app        # or: python backend/app.py
# open http://localhost:5000
```

### Getting PayPal sandbox credentials (3 steps)

1. Go to **https://developer.paypal.com** and log in (create a free PayPal account if you don't have one).
2. Open the **Apps & Credentials** page (under "My Apps & Credentials"), stay on the **Sandbox** tab, and click **Create app**. Give it any name (e.g. `escrowease`) — this creates a sandbox REST app and gives you a **Client ID**.
3. Click into the new app, reveal and copy the **Secret**. Paste both into your `.env` as `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`.

PayPal also gives you sandbox **buyer** and **merchant** test accounts on the "Sandbox Accounts" page — use the buyer's login to approve the escrow order during the demo.

Without credentials the app still runs: the header shows "Sandbox credentials not configured" and the Fund button is disabled with a clear message instead of crashing.

### Plugging in your own AI endpoint

By default the referee uses the free Pollinations text API (no key needed). To use OpenAI or any compatible endpoint:

```bash
AI_API_URL=https://api.openai.com
AI_API_KEY=sk-...
AI_MODEL=gpt-4o-mini
```

If the AI API is unreachable, a transparent local heuristic runs instead and labels itself `[fallback heuristic]` in the verdict reasons — you'll always know which verdicts are real AI judgements.

### 🏆 Nebius x NVIDIA Global AI Hackathon entry

EscrowEase is also entered in the **Nebius x NVIDIA Global AI Hackathon** (Best Apps & Agents track). For that entry, the AI referee runs on **NVIDIA Nemotron** served through **Nebius Token Factory**:

```bash
AI_API_URL=https://api.tokenfactory.nebius.com/v1
AI_API_KEY=v1-your-token-factory-key   # keep in .env, never commit
AI_MODEL=nvidia/nemotron-3-super-120b-a12b
```

Every referee verdict then makes a live runtime call to the Token Factory inference API using an NVIDIA open model (the app labels these verdicts `source: "nebius"`). $25 of Token Factory credits covers thousands of verdicts at Nemotron 3 Super pricing.

## Demo flow (for the video)

1. **Create a deal** — title, brief with concrete requirements, amount, client + freelancer emails.
2. **Fund escrow** — redirected to PayPal sandbox, log in with the sandbox buyer account, approve → redirected back → status becomes FUNDED.
3. **Submit deliverable** (as the freelancer) — describe the work, paste a link.
4. **Run AI check** — the referee returns APPROVE/REQUEST_CHANGES with confidence + reasons.
5. **Release payment** — PayPal captures the authorization → RELEASED. (Or **Refund** → PayPal voids → REFUNDED.)

See `DEMO_SCRIPT.md` for the click-by-click 90-second video script.

## What's sandbox vs production

| Piece | This prototype | Production would need |
|---|---|---|
| PayPal | Sandbox REST API (`api-m.sandbox.paypal.com`), test money only | Live credentials, webhooks for payment events, idempotency keys |
| AI referee | Pollinations free API / any OpenAI-compatible endpoint | Pinned model version, eval set, human appeal flow |
| Auth | None — demo roles are just buttons | Real user accounts, role-based access (client vs freelancer) |
| DB | SQLite file | Postgres, migrations |
| Secrets | `.env` file | Secret manager |

## Files

```
escrowease/
├── backend/
│   ├── app.py            # Flask routes + state machine
│   ├── db.py             # SQLite helpers
│   ├── paypal_client.py  # real PayPal sandbox REST calls
│   └── ai_referee.py     # judge_deliverable() — Pollinations / OpenAI-compatible / fallback
├── templates/            # home, create deal, deal detail
├── static/styles.css
├── schema.sql
├── requirements.txt
├── .env.example          # placeholders only — never real credentials
├── README.md
└── DEMO_SCRIPT.md        # 90-second video walkthrough
```

## License

MIT — do whatever you want with it.
