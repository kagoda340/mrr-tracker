# MRR Tracker - Subscription Revenue SaaS

A complete subscription billing and revenue analytics SaaS application with real Stripe payment integration.

## Features

- **Subscription Management**: Create, track, and manage subscriptions across plans (Free/Starter/Pro/Enterprise)
- **Revenue Analytics**: MRR tracking, revenue by plan, revenue timeline, gateway breakdown
- **Customer Management**: Track customers and their subscription history
- **Transaction Tracking**: Multi-gateway support (Stripe, PayPal, Crypto, Manual)
- **Web Dashboard**: Beautiful dark-themed web UI with real-time data
- **Stripe Checkout**: Built-in Stripe integration for subscription payments

## Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings httpx stripe python-dotenv jinja2 gunicorn

# Set up Stripe (see STRIPE_SETUP.md)
export STRIPE_SECRET_KEY=sk_test_...
export STRIPE_PUBLISHABLE_KEY=pk_test_...

# Run
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## Public URLs

Once deployed:
- Dashboard: https://mrr-tracker.your-domain.com/
- API: https://mrr-tracker.your-domain.com/api/

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard |
| `/health` | GET | Health check |
| `/customers` | POST/GET | Create/list customers |
| `/subscriptions` | POST/GET | Create/list subscriptions |
| `/subscriptions/{id}` | GET/PUT | Get/update subscription |
| `/transactions` | POST/GET | Create/list transactions |
| `/revenue/summary` | GET | MRR summary |
| `/revenue/by-plan` | GET | Revenue by plan |
| `/revenue/timeline?days=N` | GET | Revenue timeline |
| `/dashboard` | GET | Full dashboard data |
| `/checkout` | POST | Stripe checkout session |

## Pricing Plans

| Plan | Price | Features |
|------|-------|----------|
| Free | $0/mo | Basic dashboard, 3 subscriptions |
| Starter | $9.99/mo | Up to 20 subscriptions, analytics |
| Pro | $29/mo | Unlimited, multi-gateway, API |
| Enterprise | $99/mo | Custom integrations, SLA |

## Deployment

### Render (recommended for free tier)
1. Push to GitHub
2. Connect to Render
3. Set `STRIPE_SECRET_KEY` and `STRIPE_PUBLISHABLE_KEY` as environment variables
4. Deploy!

### Docker
```bash
docker build -t mrr-tracker .
docker run -p 8001:8001 mrr-tracker
```

## Stripe Setup

See STRIPE_SETUP.md for complete instructions.

## Tech Stack

- FastAPI (Python web framework)
- SQLite (database)
- Stripe (payments)
- Vanilla JS (frontend)
- Gunicorn (production server)
