# EscrowEase — Devpost story (Nebius x NVIDIA Global AI Hackathon)

## Inspiration

Freelance platforms have a trust problem. Clients pay upfront and pray; freelancers deliver work and chase invoices. Escrow solves the money part — hold funds until the work is done — but someone still has to *judge* the work. Today that's a human support agent, a dispute process that takes days, or just vibes.

We asked: what if the referee was an AI that reads the brief, reads the deliverable, and issues a verdict in seconds — powered by an NVIDIA open model running on independent infrastructure?

## What it does

**EscrowEase** is freelance escrow with an AI referee:

1. **Client** creates a deal and funds escrow (PayPal sandbox authorization holds the money — nothing charged yet).
2. **Freelancer** submits the deliverable (description + link).
3. The **AI referee** — NVIDIA Nemotron 3 Super, served live through Nebius Token Factory — compares the deliverable against the brief and returns a verdict: `APPROVE` or `REQUEST_CHANGES`, with a confidence score and specific reasons citing which brief requirements were met or missed.
4. On approval, the client **releases** payment (PayPal captures the authorization). If it goes wrong, the client **refunds** (PayPal voids it).

Every referee verdict is a real runtime call to the Token Factory inference API — no mocks, no cached answers. The app labels each verdict with its source so you always know which judgements came from Nemotron.

## How I built it

- **Backend:** Flask + SQLite, single deployable app.
- **Money:** PayPal sandbox REST API (OAuth → Orders with `intent=AUTHORIZE` → authorize → capture / void). Real API calls, full state machine: `DRAFT → FUNDED → DELIVERED → APPROVED/CHANGES_REQUESTED → RELEASED/REFUNDED`.
- **AI referee:** calls `https://api.tokenfactory.nebius.com/v1/chat/completions` with `nvidia/nemotron-3-super-120b-a12b`, asking for a strict JSON verdict. Nemotron is a reasoning model, so the referee reads `reasoning_content` when the regular content field comes back empty, and parses the verdict out robustly (handles markdown fences and stray text).
- **Frontend:** plain HTML/CSS/JS, no build step — the demo runs anywhere.

The whole Nebius integration is three environment variables (`AI_API_URL`, `AI_API_KEY`, `AI_MODEL`) — the referee was designed from day one to point at any OpenAI-compatible endpoint, and Token Factory speaks that protocol.

## Challenges I ran into

- **Reasoning-model output shape.** Nemotron 3 Super puts its answer in `reasoning_content` and can leave `content` empty. The first version of the referee saw empty replies and fell back to the local heuristic. Fixed by reading `reasoning_content` as the primary answer source for Nebius calls.
- **Strict JSON from a chatty model.** Reasoning models like to think out loud. The referee prompt demands a single JSON object, and the parser strips fences and extracts the first `{...}` block as a safety net — verdicts stay machine-readable for the state machine.
- **Nebius account setup.** Token Factory required a billing profile before issuing API keys; the hackathon's $25 promo credit path got me in without a card. Documented the whole path in the README so judges can reproduce it.

## Accomplishments that I'm proud of

- A working escrow product, not a demo mock: real PayPal sandbox money movements plus a real AI judgement call on every deal.
- The referee genuinely reasons — its verdicts cite specific brief requirements ("deliverable covers X, but Y is missing"), which is exactly what a human escrow agent would write.
- One codebase, two hackathons: the same app is also my PayPal AI Hackathon entry, with the AI provider cleanly swappable via env config.

## What I learned

- NVIDIA's open models on Nebius are genuinely easy to adopt: OpenAI-compatible endpoint, swap the base URL and model ID, handle the reasoning output shape, done.
- Escrow is a perfect fit for AI referees — the decision is bounded (brief vs. deliverable), auditable (reasons + confidence), and high-value (real money moves on it).
- Promo credits + clear docs make or break hackathon onboarding; the $25 Token Factory credit covered the entire build and then some.

## What's next for EscrowEase

- **Milestone-based escrow:** split deals into phases, each with its own AI verdict.
- **Evidence attachments:** let the referee inspect linked files/screenshots, not just descriptions.
- **Reputation graph:** freelancers build a verifiable on-chain-style record of approved deliverables.
- **Production hardening:** real PayPal (not sandbox), auth, and dispute escalation to a human when confidence is low.
