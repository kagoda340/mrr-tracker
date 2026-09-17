"""Stripe payment service for all 3 micro-SaaS products."""
import stripe
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Initialize Stripe
STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")

if STRIPE_SECRET:
    stripe.api_key = STRIPE_SECRET


def create_checkout_session(
    customer_email: str,
    plan_name: str,
    amount_cents: int,
    currency: str = "usd",
    interval: str = "monthly",
    success_url: str = "http://localhost:8001/success",
    cancel_url: str = "http://localhost:8001/cancel",
    product_desc: str = "",
) -> Dict[str, Any]:
    """Create a Stripe Checkout session."""
    if not STRIPE_SECRET:
        return {"error": "Stripe not configured", "mode": "simulated"}
    
    interval_stripe = interval.replace("monthly", "month").replace("yearly", "year")
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription" if interval != "one-time" else "payment",
            line_items=[{
                "price_data": {
                    "currency": currency,
                    "product_data": {
                        "name": plan_name,
                        "description": product_desc or f"${amount_cents/100:.2f}/{interval}",
                    },
                    "unit_amount": amount_cents,
                    "recurring": {"interval": interval_stripe} if interval_stripe in ("month", "year", "week", "day") else None,
                },
                "quantity": 1,
            }],
            customer_email=customer_email,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return {"session_id": session.id, "url": session.url, "mode": "live"}
    except Exception as e:
        return {"error": str(e), "mode": "live"}


def get_publishable_key() -> str:
    """Return the Stripe publishable key for frontend use."""
    return STRIPE_PUBLISHABLE


def is_stripe_configured() -> bool:
    """Check if Stripe is configured."""
    return bool(STRIPE_SECRET and STRIPE_PUBLISHABLE)


# Pricing plans for each product
PRICING_PLANS = {
    "mrr-tracker": [
        {"id": "free", "name": "Free", "price": 0, "interval": "monthly", "features": ["Basic dashboard", "3 subscriptions", "Email support"]},
        {"id": "starter", "name": "Starter", "price": 999, "interval": "monthly", "features": ["Up to 20 subscriptions", "Revenue analytics", "Transaction history", "Priority support"]},
        {"id": "pro", "name": "Pro", "price": 2900, "interval": "monthly", "features": ["Unlimited subscriptions", "Advanced analytics", "Multi-gateway support", "API access", "Priority support"]},
        {"id": "enterprise", "name": "Enterprise", "price": 9900, "interval": "monthly", "features": ["Everything in Pro", "Custom integrations", "Dedicated support", "SLA guarantee", "White-label options"]},
    ],
    "feature-hub": [
        {"id": "free", "name": "Free", "price": 0, "interval": "monthly", "features": ["Up to 10 feature requests", "Basic voting", "Email notifications"]},
        {"id": "pro", "name": "Pro", "price": 1999, "interval": "monthly", "features": ["Unlimited feature requests", "Advanced voting", "Priority notifications", "Team collaboration", "API access"]},
        {"id": "enterprise", "name": "Enterprise", "price": 4999, "interval": "monthly", "features": ["Everything in Pro", "Custom workflows", "SSO integration", "Dedicated support", "Audit logs"]},
    ],
    "analytics-pro": [
        {"id": "free", "name": "Free", "price": 0, "interval": "monthly", "features": ["1,000 events/day", "Basic dashboard", "7-day data retention"]},
        {"id": "pro", "name": "Pro", "price": 1499, "interval": "monthly", "features": ["50,000 events/day", "Advanced analytics", "Conversion funnels", "Unlimited data retention", "Export to CSV/JSON"]},
        {"id": "enterprise", "name": "Enterprise", "price": 4999, "interval": "monthly", "features": ["Unlimited events", "Custom dashboards", "Team collaboration", "Dedicated support", "SLA guarantee"]},
    ],
}
