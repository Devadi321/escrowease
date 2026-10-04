# EscrowEase — Devpost story (PayPal AI Hackathon)

## Inspiration

Freelance work runs on trust, and trust keeps breaking. Clients pay upfront and pray the work arrives. Freelancers deliver and chase invoices for weeks. Escrow fixes the money half — hold the funds until the work is done — but then someone has to *judge* the work. Today that's a support ticket, a dispute process that takes days, or just vibes.

EscrowEase asks: what if the referee was an AI agent that reads the brief, reads the deliverable, and issues a verdict in seconds — and the money moves on that verdict automatically through PayPal?

## What it does

**EscrowEase** is freelance escrow with an AI referee, built on real PayPal sandbox money movements:

1. **Client** creates a deal and funds escrow — a PayPal sandbox order with `intent=AUTHORIZE` holds the money. Nothing is charged yet.
2. **Freelancer** submits the deliverable (description + link).
3. The **AI referee** compares the deliverable against the brief and returns a verdict — `APPROVE` or `REQUEST_CHANGES` — with a confidence score and specific reasons citing which brief requirements were met or missed.
4. On approval, the client **releases** payment — PayPal **captures** the authorization and the freelancer gets paid. If it goes wrong, the client **refunds** — PayPal **voids** the authorization and the money goes back.

Full state machine, enforced in code: `DRAFT → FUNDED → DELIVERED → APPROVED/CHANGES_REQUESTED → RELEASED/REFUNDED`. Every transition is a real PayPal sandbox API call.

## How we built it

- **Backend:** Flask + SQLite, one deployable app, no build step.
- **Agentic commerce (the PayPal part):** real PayPal sandbox REST integration — OAuth 2.0 client-credentials flow, Orders v2 with `AUTHORIZE` intent, then authorize / capture / void on the Payments API. The escrow hold, the release, and the refund are all genuine PayPal money movements in the sandbox.
- **AI referee:** a pluggable judge. It sends the brief + deliverable to an AI model with a strict-JSON verdict prompt (`APPROVE`/`REQUEST_CHANGES`, confidence, reasons), with a transparent local heuristic as fallback so the state machine never stalls. The referee is designed around any OpenAI-compatible endpoint — model, URL and key are three env vars.
- **Frontend:** plain HTML/CSS/JS deal dashboard — create deals, fund them, submit deliverables, request AI verdicts, release or refund.

## Challenges we ran into

- **PayPal sandbox provisioning.** Fresh sandbox REST apps on a new developer account returned `invalid_client` for every credential pair for a full day — the account, not the code. Fixed by creating a brand-new sandbox app, which issued a working pair immediately. Lesson: when PayPal says your client ID doesn't exist, believe it and mint a new app.
- **Strict JSON from a chatty judge.** The referee prompt demands a single JSON object, but models think out loud. The parser strips markdown fences and extracts the first `{...}` block as a safety net, so verdicts stay machine-readable for the state machine.
- **Approval is human.** The authorize step needs a real buyer approval in the PayPal sandbox checkout — that click can't be automated, so the app generates the approval URL and picks the flow back up after the redirect.

## Accomplishments that we're proud of

- A working escrow product, not a mock: real PayPal sandbox authorizations, captures and voids, plus a real AI judgement call on every deal.
- The referee writes like a human escrow agent — its verdicts cite specific brief requirements ("deliverable covers X, but Y is missing") instead of a bare pass/fail.
- A complete, honest state machine: money can only move through the legal transitions, and every edge (refund, change-request) is handled.

## What we learned

- PayPal's authorize/capture/void trio maps *perfectly* onto escrow semantics: hold, release, refund. It's the rare hackathon integration where the API was designed for exactly your use case.
- Escrow is a natural fit for AI referees — the decision is bounded (brief vs. deliverable), auditable (reasons + confidence score), and high-stakes (real money moves on it).
- Agentic commerce isn't just "pay with AI" — it's AI making the *judgement* that money moves on. The payment rail is the easy part; the verdict is the product.

## What's next for EscrowEase

- **Milestone-based escrow:** split deals into phases, each with its own AI verdict and partial capture.
- **Evidence attachments:** let the referee inspect linked files and screenshots, not just text descriptions.
- **Multi-party deals:** client, freelancer, and a platform fee split in one capture.
- **Live mode:** the code paths are identical — flipping to production is a credentials change.
