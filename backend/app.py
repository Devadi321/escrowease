"""EscrowEase — freelancer escrow with an AI referee (PayPal sandbox + AI)."""
import os
import sys

# Make `python backend/app.py` work from the project root as well as `python -m backend.app`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from flask import (
    Flask, flash, g, redirect, render_template, request, url_for,
)

from backend import ai_referee, db, paypal_client

load_dotenv()

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
    static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"),
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "escrowease-dev-key")

db.init_db()

STATUS_LABELS = {
    "DRAFT": "Draft",
    "FUNDED": "Funded (escrow held)",
    "DELIVERED": "Deliverable submitted",
    "APPROVED": "AI approved",
    "CHANGES_REQUESTED": "Changes requested",
    "RELEASED": "Payment released",
    "REFUNDED": "Refunded",
}

TIMELINE = ["DRAFT", "FUNDED", "DELIVERED", "VERDICT", "SETTLED"]


def deal_or_404(deal_id):
    deal = db.get_deal(deal_id)
    if deal is None:
        flash("Deal not found.", "error")
        return None
    return deal


def require_status(deal, *allowed):
    if deal["status"] not in allowed:
        flash(f"That action isn't available while the deal is '{deal['status']}'.", "error")
        return False
    return True


@app.context_processor
def inject_globals():
    return {
        "status_labels": STATUS_LABELS,
        "paypal_configured": paypal_client.is_configured(),
    }


@app.route("/")
def index():
    deals = db.list_deals()
    return render_template("index.html", deals=deals)


@app.route("/deals/new", methods=["GET", "POST"])
def new_deal():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        brief = request.form.get("brief", "").strip()
        amount = request.form.get("amount", "").strip()
        currency = request.form.get("currency", "USD").strip().upper() or "USD"
        client_email = request.form.get("client_email", "").strip()
        freelancer_email = request.form.get("freelancer_email", "").strip()
        try:
            amount_f = float(amount)
            if amount_f <= 0:
                raise ValueError
        except ValueError:
            flash("Amount must be a number greater than 0.", "error")
            return render_template("create.html", form=request.form)
        if not (title and brief and client_email and freelancer_email):
            flash("Please fill in every field.", "error")
            return render_template("create.html", form=request.form)
        deal_id = db.create_deal(title, brief, amount_f, currency, client_email, freelancer_email)
        flash("Deal created. Next: fund the escrow.", "ok")
        return redirect(url_for("deal_detail", deal_id=deal_id))
    return render_template("create.html", form={})


@app.route("/deals/<int:deal_id>")
def deal_detail(deal_id):
    deal = deal_or_404(deal_id)
    if deal is None:
        return redirect(url_for("index"))
    deliverables = db.list_deliverables(deal_id)
    verdict = db.latest_verdict(deal_id)
    return render_template(
        "deal.html", deal=deal, deliverables=deliverables,
        verdict=verdict, timeline=TIMELINE,
    )


# ---- PayPal escrow flow ----
@app.route("/deals/<int:deal_id>/fund", methods=["POST"])
def fund(deal_id):
    deal = deal_or_404(deal_id)
    if deal is None:
        return redirect(url_for("index"))
    if not require_status(deal, "DRAFT"):
        return redirect(url_for("deal_detail", deal_id=deal_id))
    try:
        order_id, approve_url = paypal_client.create_order(
            amount=deal["amount"],
            currency=deal["currency"],
            description=f"EscrowEase: {deal['title']}",
            return_url=url_for("fund_return", deal_id=deal_id, _external=True),
            cancel_url=url_for("fund_cancel", deal_id=deal_id, _external=True),
        )
    except paypal_client.PayPalNotConfigured as e:
        flash(str(e), "error")
        return redirect(url_for("deal_detail", deal_id=deal_id))
    except paypal_client.PayPalError as e:
        flash(f"PayPal error: {e}", "error")
        return redirect(url_for("deal_detail", deal_id=deal_id))
    db.update_deal(deal_id, paypal_order_id=order_id)
    # Buyer approves on PayPal's site, then PayPal redirects to fund_return.
    return redirect(approve_url)


@app.route("/deals/<int:deal_id>/fund/return")
def fund_return(deal_id):
    deal = deal_or_404(deal_id)
    if deal is None:
        return redirect(url_for("index"))
    order_id = deal["paypal_order_id"]
    if not order_id:
        flash("No PayPal order found for this deal.", "error")
        return redirect(url_for("deal_detail", deal_id=deal_id))
    try:
        auth_id = paypal_client.authorize_order(order_id)
    except (paypal_client.PayPalNotConfigured, paypal_client.PayPalError) as e:
        flash(f"Could not lock escrow funds: {e}", "error")
        return redirect(url_for("deal_detail", deal_id=deal_id))
    db.update_deal(deal_id, paypal_auth_id=auth_id, status="FUNDED")
    flash("Escrow funded — payment is authorized and held by PayPal.", "ok")
    return redirect(url_for("deal_detail", deal_id=deal_id))


@app.route("/deals/<int:deal_id>/fund/cancel")
def fund_cancel(deal_id):
    flash("Funding was cancelled on PayPal — no money moved.", "error")
    return redirect(url_for("deal_detail", deal_id=deal_id))


@app.route("/deals/<int:deal_id>/release", methods=["POST"])
def release(deal_id):
    """Capture the authorization -> freelancer gets paid."""
    deal = deal_or_404(deal_id)
    if deal is None:
        return redirect(url_for("index"))
    if not require_status(deal, "APPROVED"):
        return redirect(url_for("deal_detail", deal_id=deal_id))
    try:
        capture_id = paypal_client.capture_authorization(deal["paypal_auth_id"])
    except (paypal_client.PayPalNotConfigured, paypal_client.PayPalError) as e:
        flash(f"Could not release payment: {e}", "error")
        return redirect(url_for("deal_detail", deal_id=deal_id))
    db.update_deal(deal_id, status="RELEASED")
    flash(f"Payment released! PayPal capture id: {capture_id}", "ok")
    return redirect(url_for("deal_detail", deal_id=deal_id))


@app.route("/deals/<int:deal_id>/refund", methods=["POST"])
def refund(deal_id):
    """Void the authorization -> client gets money back."""
    deal = deal_or_404(deal_id)
    if deal is None:
        return redirect(url_for("index"))
    if not require_status(deal, "FUNDED", "DELIVERED", "APPROVED", "CHANGES_REQUESTED"):
        return redirect(url_for("deal_detail", deal_id=deal_id))
    try:
        paypal_client.void_authorization(deal["paypal_auth_id"])
    except (paypal_client.PayPalNotConfigured, paypal_client.PayPalError) as e:
        flash(f"Could not refund: {e}", "error")
        return redirect(url_for("deal_detail", deal_id=deal_id))
    db.update_deal(deal_id, status="REFUNDED")
    flash("Escrow voided — the authorization was released back to the client.", "ok")
    return redirect(url_for("deal_detail", deal_id=deal_id))


# ---- Deliverables + AI referee ----
@app.route("/deals/<int:deal_id>/deliver", methods=["POST"])
def deliver(deal_id):
    deal = deal_or_404(deal_id)
    if deal is None:
        return redirect(url_for("index"))
    if not require_status(deal, "FUNDED", "CHANGES_REQUESTED"):
        return redirect(url_for("deal_detail", deal_id=deal_id))
    description = request.form.get("description", "").strip()
    link = request.form.get("link", "").strip()
    if not description:
        flash("Please describe what you delivered.", "error")
        return redirect(url_for("deal_detail", deal_id=deal_id))
    db.add_deliverable(deal_id, description, link)
    db.update_deal(deal_id, status="DELIVERED")
    flash("Deliverable submitted. Run the AI check when ready.", "ok")
    return redirect(url_for("deal_detail", deal_id=deal_id))


@app.route("/deals/<int:deal_id>/ai-check", methods=["POST"])
def ai_check(deal_id):
    deal = deal_or_404(deal_id)
    if deal is None:
        return redirect(url_for("index"))
    if not require_status(deal, "DELIVERED"):
        return redirect(url_for("deal_detail", deal_id=deal_id))
    deliverable = db.latest_deliverable(deal_id)
    if deliverable is None:
        flash("No deliverable to judge yet.", "error")
        return redirect(url_for("deal_detail", deal_id=deal_id))
    verdict = ai_referee.judge_deliverable(
        deal["brief"], deliverable["description"], deliverable["link"] or ""
    )
    db.add_verdict(
        deal_id, verdict["decision"], verdict["confidence"],
        verdict["reasons"], verdict["source"],
    )
    new_status = "APPROVED" if verdict["decision"] == "APPROVE" else "CHANGES_REQUESTED"
    db.update_deal(deal_id, status=new_status)
    if verdict["source"] == "fallback":
        flash("AI API unreachable — verdict used the transparent local fallback.", "error")
    else:
        flash(f"AI referee verdict: {verdict['decision']} ({verdict['confidence']}% confident).", "ok")
    return redirect(url_for("deal_detail", deal_id=deal_id))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
