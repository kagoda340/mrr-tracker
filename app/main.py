"""MRR Tracker — Payment management & revenue analytics API."""
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional
import sqlite3
import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "mmr.db")

app = FastAPI(title="MRR Tracker", version="1.0.0", description="Subscription billing & revenue analytics")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

@app.get("/")
async def serve_frontend():
    """Serve the web frontend."""
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "ok", "service": "mmr-tracker", "version": "1.0.0", "message": "API running. Web UI available."}


@app.get("/config")
async def get_config():
    """Return configuration (Stripe keys etc)."""
    return {
        "stripe_key": os.environ.get("STRIPE_PUBLISHABLE_KEY", ""),
        "stripe_secret_configured": bool(os.environ.get("STRIPE_SECRET_KEY", "")),
        "stripe_enabled": bool(os.environ.get("STRIPE_SECRET_KEY", "") and os.environ.get("STRIPE_PUBLISHABLE_KEY", "")),
    }

@app.get("/pricing")
async def get_pricing():
    """Return pricing plans."""
    return {
        "plans": [
            {"id": "free", "name": "Free", "price_cents": 0, "interval": "monthly", "features": ["Basic dashboard", "3 subscriptions", "Email support"]},
            {"id": "starter", "name": "Starter", "price_cents": 999, "interval": "monthly", "features": ["Up to 20 subscriptions", "Revenue analytics", "Transaction history", "Priority support"]},
            {"id": "pro", "name": "Pro", "price_cents": 2900, "interval": "monthly", "features": ["Unlimited subscriptions", "Advanced analytics", "Multi-gateway support", "API access", "Priority support"]},
            {"id": "enterprise", "name": "Enterprise", "price_cents": 9900, "interval": "monthly", "features": ["Everything in Pro", "Custom integrations", "Dedicated support", "SLA guarantee", "White-label options"]},
        ]
    }


# --- Models ---
class SubscriptionCreate(BaseModel):
    customer_id: str
    plan: str = Field(..., pattern="^(free|starter|pro|enterprise)$")
    amount_cents: int = Field(..., ge=0)
    currency: str = "usd"
    interval: str = Field(..., pattern="^(monthly|yearly)$")
    start_date: str

class SubscriptionUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|cancelled|paused|expired)$")

class TransactionCreate(BaseModel):
    subscription_id: str
    amount_cents: int = Field(..., ge=0)
    type: str = Field(..., pattern="^(recurring|one-time|refund|chargeback)$")
    gateway: str = Field(..., pattern="^(stripe|paypal|crypto|manual)$")
    status: str = Field(..., pattern="^(success|failed|pending|refunded)$")


# --- Database ---
def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            plan TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            currency TEXT NOT NULL,
            interval TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            start_date TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            subscription_id TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            type TEXT NOT NULL,
            gateway TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (subscription_id) REFERENCES subscriptions(id)
        );
    """)
    conn.close()

init_db()


# --- Endpoints ---
@app.get("/")
async def root():
    return {"status": "ok", "service": "mmr-tracker", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# Customers
@app.post("/customers")
async def create_customer(name: str, email: str):
    cid = str(uuid.uuid4())[:8]
    conn = get_db()
    conn.execute("INSERT INTO customers (id, name, email, created_at) VALUES (?, ?, ?, ?)",
                 (cid, name, email, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return {"id": cid, "name": name, "email": email, "created_at": datetime.utcnow().isoformat()}

@app.get("/customers")
async def list_customers():
    conn = get_db()
    rows = conn.execute("SELECT * FROM customers ORDER BY created_at DESC").fetchall()
    conn.close()
    return [{"id": r["id"], "name": r["name"], "email": r["email"], "created_at": r["created_at"]} for r in rows]


# Subscriptions
@app.post("/subscriptions")
async def create_subscription(sub: SubscriptionCreate):
    sid = str(uuid.uuid4())[:8]
    conn = get_db()
    conn.execute(
        "INSERT INTO subscriptions (id, customer_id, plan, amount_cents, currency, interval, status, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (sid, sub.customer_id, sub.plan, sub.amount_cents, sub.currency, sub.interval, "active", sub.start_date, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return {"id": sid, **sub.model_dump(), "status": "active"}

@app.get("/subscriptions")
async def list_subscriptions(status: Optional[str] = Query(None)):
    conn = get_db()
    if status:
        rows = conn.execute("SELECT * FROM subscriptions WHERE status = ?", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM subscriptions").fetchall()
    conn.close()
    return [{"id": r["id"], "customer_id": r["customer_id"], "plan": r["plan"],
             "amount_cents": r["amount_cents"], "currency": r["currency"],
             "interval": r["interval"], "status": r["status"],
             "start_date": r["start_date"]} for r in rows]

@app.put("/subscriptions/{sub_id}")
async def update_subscription(sub_id: str, sub: SubscriptionUpdate):
    conn = get_db()
    cur = conn.execute("UPDATE subscriptions SET status = ? WHERE id = ?", (sub.status, sub_id))
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Subscription not found")
    row = conn.execute("SELECT * FROM subscriptions WHERE id = ?", (sub_id,)).fetchone()
    conn.close()
    return {"id": row["id"], "status": row["status"]}

@app.get("/subscriptions/{sub_id}")
async def get_subscription(sub_id: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM subscriptions WHERE id = ?", (sub_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Subscription not found")
    return {"id": row["id"], "customer_id": row["customer_id"], "plan": row["plan"],
            "amount_cents": row["amount_cents"], "currency": row["currency"],
            "interval": row["interval"], "status": row["status"],
            "start_date": row["start_date"]}


# Transactions
@app.post("/transactions")
async def create_transaction(txn: TransactionCreate):
    tid = str(uuid.uuid4())[:8]
    conn = get_db()
    conn.execute(
        "INSERT INTO transactions (id, subscription_id, amount_cents, type, gateway, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (tid, txn.subscription_id, txn.amount_cents, txn.type, txn.gateway, txn.status, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return {"id": tid, **txn.model_dump(), "created_at": datetime.utcnow().isoformat()}

@app.get("/transactions")
async def list_transactions(subscription_id: Optional[str] = Query(None), status: Optional[str] = Query(None)):
    conn = get_db()
    if subscription_id:
        rows = conn.execute("SELECT * FROM transactions WHERE subscription_id = ? ORDER BY created_at DESC", (subscription_id,)).fetchall()
    elif status:
        rows = conn.execute("SELECT * FROM transactions WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM transactions ORDER BY created_at DESC").fetchall()
    conn.close()
    return [{"id": r["id"], "subscription_id": r["subscription_id"], "amount_cents": r["amount_cents"],
             "type": r["type"], "gateway": r["gateway"], "status": r["status"],
             "created_at": r["created_at"]} for r in rows]


# Revenue Analytics
@app.get("/revenue/summary")
async def revenue_summary(start_date: Optional[str] = Query(None), end_date: Optional[str] = Query(None)):
    conn = get_db()
    query = """
        SELECT 
            COUNT(DISTINCT s.id) as active_subscriptions,
            SUM(s.amount_cents) as total_mrr_cents,
            COUNT(t.id) as total_transactions,
            SUM(CASE WHEN t.status = 'success' THEN t.amount_cents ELSE 0 END) as total_revenue_cents,
            SUM(CASE WHEN t.status = 'refunded' OR t.type = 'refund' THEN t.amount_cents ELSE 0 END) as total_refunds_cents
        FROM subscriptions s
        LEFT JOIN transactions t ON s.id = t.subscription_id
        WHERE s.status = 'active'
    """
    params = []
    if start_date:
        query += " AND s.start_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND s.start_date <= ?"
        params.append(end_date)
    
    row = conn.execute(query, params).fetchone()
    conn.close()
    
    if not row:
        return {"error": "No data"}
    
    return {
        "active_subscriptions": row["active_subscriptions"] or 0,
        "total_mrr_cents": row["total_mrr_cents"] or 0,
        "total_mrr_usd": round((row["total_mrr_cents"] or 0) / 100, 2),
        "total_transactions": row["total_transactions"] or 0,
        "total_revenue_cents": row["total_revenue_cents"] or 0,
        "total_revenue_usd": round((row["total_revenue_cents"] or 0) / 100, 2),
        "total_refunds_cents": row["total_refunds_cents"] or 0,
        "net_revenue_usd": round(((row["total_revenue_cents"] or 0) - (row["total_refunds_cents"] or 0)) / 100, 2),
    }

@app.get("/revenue/by-plan")
async def revenue_by_plan():
    conn = get_db()
    rows = conn.execute("""
        SELECT plan, COUNT(*) as count, SUM(amount_cents) as mrr_cents
        FROM subscriptions
        WHERE status = 'active'
        GROUP BY plan
        ORDER BY mrr_cents DESC
    """).fetchall()
    conn.close()
    return [{"plan": r["plan"], "count": r["count"], "mrr_cents": r["mrr_cents"],
             "mrr_usd": round(r["mrr_cents"] / 100, 2)} for r in rows]

@app.get("/revenue/by-gateway")
async def revenue_by_gateway():
    conn = get_db()
    rows = conn.execute("""
        SELECT gateway, COUNT(*) as count, SUM(amount_cents) as total_cents
        FROM transactions
        WHERE status = 'success'
        GROUP BY gateway
        ORDER BY total_cents DESC
    """).fetchall()
    conn.close()
    return [{"gateway": r["gateway"], "count": r["count"],
             "total_cents": r["total_cents"],
             "total_usd": round(r["total_cents"] / 100, 2)} for r in rows]

@app.get("/revenue/timeline")
async def revenue_timeline(days: int = Query(30, ge=1, le=365)):
    conn = get_db()
    rows = conn.execute(f"""
        SELECT DATE(created_at) as day, 
               SUM(CASE WHEN type = 'recurring' THEN amount_cents ELSE 0 END) as recurring_cents,
               SUM(CASE WHEN type = 'one-time' THEN amount_cents ELSE 0 END) as onetime_cents,
               SUM(amount_cents) as total_cents
        FROM transactions
        WHERE status = 'success' AND created_at >= date('now', '-' || ? || ' days')
        GROUP BY day
        ORDER BY day
    """, (days,)).fetchall()
    conn.close()
    return [{"date": r["day"], "recurring_cents": r["recurring_cents"] or 0,
             "recurring_usd": round((r["recurring_cents"] or 0) / 100, 2),
             "onetime_cents": r["onetime_cents"] or 0,
             "onetime_usd": round((r["onetime_cents"] or 0) / 100, 2),
             "total_cents": r["total_cents"] or 0,
             "total_usd": round((r["total_cents"] or 0) / 100, 2)} for r in rows]


# Dashboard
@app.get("/dashboard")
async def dashboard():
    conn = get_db()
    stats = conn.execute("""
        SELECT 
            (SELECT COUNT(*) FROM customers) as total_customers,
            (SELECT COUNT(*) FROM subscriptions WHERE status = 'active') as active_subs,
            (SELECT COUNT(*) FROM subscriptions WHERE status = 'cancelled') as cancelled_subs,
            (SELECT COUNT(*) FROM transactions WHERE status = 'success') as successful_txns,
            (SELECT COUNT(*) FROM transactions WHERE status = 'failed') as failed_txns,
            (SELECT SUM(amount_cents) FROM subscriptions WHERE status = 'active') as total_mrr,
            (SELECT SUM(amount_cents) FROM transactions WHERE status = 'success') as total_revenue,
            (SELECT SUM(amount_cents) FROM transactions WHERE status = 'refunded') as total_refunds
    """).fetchone()
    conn.close()
    
    return {
        "total_customers": stats["total_customers"] or 0,
        "active_subscriptions": stats["active_subs"] or 0,
        "cancelled_subscriptions": stats["cancelled_subs"] or 0,
        "successful_transactions": stats["successful_txns"] or 0,
        "failed_transactions": stats["failed_txns"] or 0,
        "total_mrr_cents": stats["total_mrr"] or 0,
        "total_mrr_usd": round((stats["total_mrr"] or 0) / 100, 2),
        "total_revenue_cents": stats["total_revenue"] or 0,
        "total_revenue_usd": round((stats["total_revenue"] or 0) / 100, 2),
        "total_refunds_cents": stats["total_refunds"] or 0,
        "net_revenue_usd": round(((stats["total_revenue"] or 0) - (stats["total_refunds"] or 0)) / 100, 2),
    }


# Stripe checkout endpoint
@app.get("/checkout")
async def create_checkout(request: Request):
    """Create a Stripe checkout session for subscription purchase."""
    body = await request.json()
    customer_email = body.get("customer_email", "")
    plan = body.get("plan", "starter")
    amount_cents = body.get("amount_cents", 999)
    interval = body.get("interval", "monthly")
    currency = body.get("currency", "usd")
    
    stripe_secret = os.environ.get("STRIPE_SECRET_KEY", "")
    stripe_pub = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    
    if not stripe_secret or not stripe_pub:
        # Simulated checkout (no Stripe configured)
        return {
            "mode": "simulated",
            "message": "Stripe not configured. Simulating payment flow.",
            "plan": plan,
            "amount": amount_cents,
            "customer_email": customer_email,
        }
    
    try:
        import stripe
        stripe.api_key = stripe_secret
        
        # Map our interval names to Stripe's
        stripe_interval = interval
        if interval == "monthly":
            stripe_interval = "month"
        elif interval == "yearly":
            stripe_interval = "year"
        
        plan_names = {"free": "Free", "starter": "Starter", "pro": "Pro", "enterprise": "Enterprise"}
        display_name = plan_names.get(plan, plan.title())
        
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
        return {"session_id": session.id, "url": session.url, "mode": "live"}
    except stripe.error.StripeError as e:
        return {"error": str(e), "mode": "live", "stripe_code": e.user_code if hasattr(e, 'user_code') else None}
    except Exception as e:
        return {"error": f"Server error: {str(e)}", "mode": "live"}


@app.get("/success")
async def checkout_success(session_id: str = Query(...)):
    """Handle successful checkout."""
    return {
        "status": "success",
        "session_id": session_id,
        "message": "Payment successful!"
    }


@app.get("/cancel")
async def checkout_cancel():
    """Handle cancelled checkout."""
    return {
        "status": "cancelled",
        "message": "Payment cancelled. No charge was made."
    }
