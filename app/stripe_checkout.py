"""Stripe checkout and pricing for MRR Tracker."""
from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
import stripe
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


@router.get("/config")
async def get_stripe_config():
    """Return Stripe configuration for frontend."""
    return {
        "stripe_publishable_key": STRIPE_PUBLISHABLE_KEY,
        "stripe_enabled": bool(STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY),
    }


@router.get("/pricing")
async def get_pricing():
    """Return pricing plans."""
    return {
        "plans": [
            {"id": "free", "name": "Free", "price_cents": 0, "interval": "monthly",
             "features": ["Basic dashboard", "3 subscriptions", "Email support"]},
            {"id": "starter", "name": "Starter", "price_cents": 999, "interval": "monthly",
             "features": ["Up to 20 subscriptions", "Revenue analytics", "Transaction history", "Priority support"]},
            {"id": "pro", "name": "Pro", "price_cents": 2900, "interval": "monthly",
             "features": ["Unlimited subscriptions", "Advanced analytics", "Multi-gateway support", "API access", "Priority support"]},
            {"id": "enterprise", "name": "Enterprise", "price_cents": 9900, "interval": "monthly",
             "features": ["Everything in Pro", "Custom integrations", "Dedicated support", "SLA guarantee", "White-label"]},
        ]
    }


@router.post("/checkout")
async def create_checkout(request: Request):
    """Create a Stripe Checkout session for subscription."""
    body = await request.json()
    customer_email = body.get("customer_email", "")
    plan_id = body.get("plan", "starter")
    amount_cents = body.get("amount_cents", 999)
    interval = body.get("interval", "monthly")
    currency = body.get("currency", "usd")
    
    if not STRIPE_SECRET_KEY or not STRIPE_PUBLISHABLE_KEY:
        return JSONResponse({
            "mode": "simulated",
            "message": "Stripe not configured. Simulating payment.",
            "plan": plan_id,
            "amount": amount_cents
        })
    
    stripe_interval = interval
    if interval == "monthly":
        stripe_interval = "month"
    elif interval == "yearly":
        stripe_interval = "year"
    
    plan_names = {"free": "Free", "starter": "Starter", "pro": "Pro", "enterprise": "Enterprise"}
    display_name = plan_names.get(plan_id, plan_id.title())
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price_data": {
                    "currency": currency,
                    "product_data": {
                        "name": f"MRR Tracker - {display_name} Plan",
                        "description": f"${amount_cents/100:.2f}/{'month' if stripe_interval == 'month' else 'year'}",
                    },
                    "unit_amount": amount_cents,
                    "recurring": {"interval": stripe_interval},
                },
                "quantity": 1,
            }],
            customer_email=customer_email,
            success_url=f"{request.base_url}success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{request.base_url}cancel",
        )
        return JSONResponse({"session_id": session.id, "url": session.url, "mode": "live"})
    except stripe.error.StripeError as e:
        return JSONResponse({"error": str(e), "mode": "live", "stripe_code": getattr(e, 'user_code', None)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e), "mode": "live"}, status_code=500)


@router.get("/success")
async def checkout_success(session_id: str = Query(...)):
    """Handle successful checkout redirect."""
    return {"status": "success", "session_id": session_id, "message": "Payment successful! Redirecting to dashboard..."}


@router.get("/cancel")
async def checkout_cancel():
    """Handle cancelled checkout redirect."""
    return {"status": "cancelled", "message": "Payment cancelled. No charge was made."}


# Include the router
app.include_router(router)
