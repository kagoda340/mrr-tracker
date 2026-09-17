"""Stripe payment service for MRR Tracker."""
import stripe
import os
from typing import Optional, Dict, Any
from decimal import Decimal

# Initialize Stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

def create_checkout_session(
    customer_email: str,
    plan: str,
    amount_cents: int,
    currency: str = "usd",
    interval: str = "monthly",
    success_url: str = "http://localhost:8001/success",
    cancel_url: str = "http://localhost:8001/cancel",
) -> Dict[str, Any]:
    """Create a Stripe Checkout session for a subscription."""
    if not stripe.api_key:
        return {"error": "STRIPE_SECRET_KEY not set", "mode": "mock"}
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price_data": {
                    "currency": currency,
                    "product_data": {
                        "name": f"{plan.title()} Plan",
                        "description": f"${amount_cents/100:.2f}/{'month' if interval == 'monthly' else 'year'}",
                    },
                    "unit_amount": amount_cents,
                    "recurring": {
                        "interval": interval,
                    },
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


def get_checkout_session(session_id: str) -> Dict[str, Any]:
    """Retrieve a checkout session."""
    if not stripe.api_key:
        return {"error": "STRIPE_SECRET_KEY not set", "mode": "mock"}
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return {
            "id": session.id,
            "status": session.status,
            "customer_email": session.customer_email,
            "amount_total": session.amount_total,
            "currency": session.currency,
            "mode": "live",
        }
    except Exception as e:
        return {"error": str(e)}


def webhook_handler(payload: bytes, sig_header: str, webhook_secret: str) -> Optional[Dict]:
    """Handle Stripe webhook events."""
    if not stripe.api_key:
        return None
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        return event
    except Exception as e:
        return {"error": str(e)}


def create_price(product_id: str, amount_cents: int, currency: str = "usd", 
                  interval: str = "monthly") -> Optional[str]:
    """Create a recurring price for a product."""
    if not stripe.api_key:
        return None
    try:
        price = stripe.Price.create(
            product=product_id,
            unit_amount=amount_cents,
            currency=currency,
            recurring={"interval": interval},
        )
        return price.id
    except Exception as e:
        return None


def create_product(name: str, description: str = "") -> Optional[str]:
    """Create a Stripe product."""
    if not stripe.api_key:
        return None
    try:
        product = stripe.Product.create(
            name=name,
            description=description,
        )
        return product.id
    except Exception as e:
        return None
