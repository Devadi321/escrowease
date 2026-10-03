"""PayPal Sandbox REST client (direct REST calls, no SDK).

Escrow flow:
  1. create_order(intent=AUTHORIZE)  -> buyer approves on paypal.com (funds held)
  2. authorize_order(order_id)       -> authorization id stored (escrow locked)
  3. capture_authorization(auth_id)  -> RELEASED (freelancer gets paid)
     OR void_authorization(auth_id)  -> REFUNDED (client gets money back)

Credentials come from env vars PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET.
Nothing is hardcoded; missing creds raise PayPalNotConfigured instead of
crashing, so the UI can show a clear "not configured" state.
"""
import os

import requests

SANDBOX_BASE = "https://api-m.sandbox.paypal.com"
TIMEOUT = 20


class PayPalNotConfigured(Exception):
    """Raised when sandbox credentials are missing or still placeholders."""


class PayPalError(Exception):
    def __init__(self, message, status=None, details=None):
        super().__init__(message)
        self.status = status
        self.details = details


def _creds():
    cid = os.environ.get("PAYPAL_CLIENT_ID", "").strip()
    secret = os.environ.get("PAYPAL_CLIENT_SECRET", "").strip()
    if (
        not cid
        or not secret
        or cid.startswith("YOUR_")
        or secret.startswith("YOUR_")
    ):
        raise PayPalNotConfigured(
            "PayPal sandbox credentials are not configured. "
            "Copy .env.example to .env and paste your sandbox REST app "
            "Client ID and Secret from developer.paypal.com."
        )
    return cid, secret


def get_access_token():
    cid, secret = _creds()
    try:
        r = requests.post(
            f"{SANDBOX_BASE}/v1/oauth2/token",
            auth=(cid, secret),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json"},
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        raise PayPalError(f"Could not reach PayPal sandbox: {e}")
    if r.status_code != 200:
        raise PayPalError(
            f"PayPal auth failed (HTTP {r.status_code}). Check that your "
            f"Client ID/Secret are from a SANDBOX REST app at developer.paypal.com.",
            status=r.status_code,
            details=_safe_body(r),
        )
    try:
        return r.json()["access_token"]
    except (ValueError, KeyError):
        raise PayPalError("PayPal returned an unexpected auth response.")


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _safe_body(response):
    try:
        return response.json()
    except ValueError:
        return (response.text or "")[:500]


def _post(path, payload):
    token = get_access_token()
    try:
        r = requests.post(
            f"{SANDBOX_BASE}{path}", json=payload, headers=_headers(token), timeout=TIMEOUT
        )
    except requests.RequestException as e:
        raise PayPalError(f"Could not reach PayPal sandbox: {e}")
    if r.status_code not in (200, 201):
        body = _safe_body(r)
        msg = f"PayPal call failed (HTTP {r.status_code})."
        if isinstance(body, dict) and body.get("message"):
            msg += f" {body['message']}"
        raise PayPalError(msg, status=r.status_code, details=body)
    try:
        return r.json()
    except ValueError:
        return {}


def create_order(amount, currency, description, return_url, cancel_url):
    """Create an AUTHORIZE-intent order; returns (order_id, approve_url)."""
    data = _post(
        "/v2/checkout/orders",
        {
            "intent": "AUTHORIZE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": currency,
                        "value": f"{float(amount):.2f}",
                    },
                    "description": (description or "EscrowEase escrow")[:127],
                }
            ],
            "application_context": {
                "brand_name": "EscrowEase",
                "user_action": "PAY_NOW",
                "return_url": return_url,
                "cancel_url": cancel_url,
            },
        },
    )
    links = {l.get("rel"): l.get("href") for l in data.get("links", [])}
    approve_url = links.get("approve")
    if not data.get("id") or not approve_url:
        raise PayPalError("PayPal did not return an order id / approve link.")
    return data["id"], approve_url


def authorize_order(order_id):
    """Authorize an approved order; returns the authorization id (escrow lock)."""
    data = _post(f"/v2/checkout/orders/{order_id}/authorize", {})
    try:
        auth = data["purchase_units"][0]["payments"]["authorizations"][0]
        return auth["id"]
    except (KeyError, IndexError, TypeError):
        raise PayPalError(
            "PayPal did not return an authorization. The buyer may not have "
            "approved the order yet.",
            details=data,
        )


def capture_authorization(auth_id):
    """Release escrow: capture the authorization (freelancer gets paid)."""
    data = _post(f"/v2/payments/authorizations/{auth_id}/capture", {})
    return data.get("id")


def void_authorization(auth_id):
    """Refund escrow: void the authorization (client gets money back)."""
    data = _post(f"/v2/payments/authorizations/{auth_id}/void", {})
    return data.get("id") or auth_id


def is_configured():
    try:
        _creds()
        return True
    except PayPalNotConfigured:
        return False
