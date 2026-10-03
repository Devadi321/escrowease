# EscrowEase — 90-second demo video script

**Setup before recording:** `.env` has sandbox Client ID + Secret. Server running on
`http://localhost:5000`. Have the PayPal **sandbox buyer** account email/password
handy (developer.paypal.com → Sandbox Accounts). Screen-record the browser at 1080p.

**Tone:** upbeat, one idea per beat. Total target: 60–90 seconds.

---

**[0:00–0:08] HOOK — the problem**
*(Show the EscrowEase home page.)*
> "Hiring a freelancer online? You pay upfront and pray — or they work for free and pray.
> EscrowEase fixes that: the client's money is held in PayPal escrow, and an AI referee
> checks the work before a single rupee — sorry, dollar — moves."

**[0:08–0:20] CREATE THE DEAL**
*(Click "Create a deal". Fill: title "Landing page copy", brief with 3–4 concrete
requirements, amount 150.00 USD, client + freelancer emails. Submit.)*
> "I create a deal with a sharp brief — headline, three benefit sections, pricing table, FAQ.
> Specific requirements matter, because the AI will check against them."

**[0:20–0:38] FUND ESCROW**
*(Click "Fund escrow via PayPal". PayPal sandbox login page appears — log in with the
sandbox buyer account. Review the $150.00 authorization, click Approve/Agree. Redirected
back — status flips to FUNDED.)*
> "I fund the escrow. PayPal authorizes — holds — the $150. Nobody's charged yet.
> We're back, and the deal is funded."

**[0:38–0:55] DELIVER + AI VERDICT**
*(Paste a deliverable description that hits every brief requirement + a link. Click
"Submit deliverable", then "Run AI check". The verdict card appears: APPROVE, confidence
bar, bullet reasons.)*
> "The freelancer submits the work. Now the AI referee reads the brief, reads the
> deliverable, and verdicts: APPROVE — 87% confident — with reasons citing each requirement."

**[0:55–1:15] RELEASE**
*(Click "Release payment". Status flips to RELEASED. Flash shows the PayPal capture id.)*
> "The client releases. PayPal captures the authorization — the freelancer gets paid,
> the client got verified work. And if the AI had flagged it? One click voids the
> authorization and the client is refunded. Trust, automated."

**[1:15–1:25] CLOSE**
*(Back on the home page showing the completed deal.)*
> "EscrowEase — freelance escrow with an AI referee. Real PayPal sandbox payments,
> real AI verdicts. Built for the PayPal AI Hackathon."

---

## Click-by-click checklist (no narration needed while doing)

1. Home → **+ Create a deal**
2. Fill form → **Create deal**
3. **💰 Fund escrow via PayPal** → sandbox login → approve → auto-redirect
4. Fill deliverable form → **📦 Submit deliverable**
5. **🤖 Run AI check** → wait ~5–15s for verdict card
6. **✅ Release payment** → RELEASED + capture id in flash message
7. (Alt ending) **↩ Refund client** → REFUNDED

## If something goes wrong live

- **AI check slow/fails** → the app falls back to a labeled heuristic verdict; say
  "and if the AI API is ever unreachable, it degrades to a clearly-labeled fallback."
- **PayPal sandbox hiccup** → sandbox is occasionally flaky; retry the fund step once.
- **Forgot credentials** → the header pill shows the state honestly; don't fake it.
