SaaS Stripe Integration Guide
=============================

This project uses Stripe for payment processing. Follow these steps to set up real payments.

STEP 1: Create a Stripe Account
-------------------------------
1. Go to https://dashboard.stripe.com/register
2. Sign up with your email
3. Complete identity verification (required for payouts)
4. Add your bank account for payouts (this is where money goes - your debit card via bank account)

STEP 2: Get API Keys
--------------------
1. In Stripe Dashboard, go to Developers > API keys
2. Copy "Secret key" (starts with sk_test_ or sk_live_)
3. Copy "Publishable key" (starts with pk_test_ or pk_live_)

STEP 3: Configure Environment
-----------------------------
Create a .env file in the project root:
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...
```

For test mode (sk_test_), use Stripe's test card numbers:
- Success: 4242 4242 4242 4242
- Decline: 4000 0000 0000 0002
- Authentication required: 4000 0025 0000 0009

STEP 4: Create Products and Prices in Stripe Dashboard
-------------------------------------------------------
1. Go to Products > Add product
2. Create products for each plan (Starter, Pro, Enterprise)
3. Add recurring prices for each
4. Copy the price IDs (price_...) to your .env

STEP 5: Set Up Webhook (for production)
-----------------------------------------
1. In Stripe Dashboard > Developers > Webhooks
2. Add endpoint: https://yourdomain.com/webhook/stripe
3. Select events: checkout.session.completed, customer.subscription.created, 
   customer.subscription.updated, customer.subscription.deleted
4. Copy the signing secret to .env as STRIPE_WEBHOOK_SECRET

STEP 6: Test in Test Mode
--------------------------
1. Start the app
2. Go to the checkout page
3. Use test card 4242 4242 4242 4242
4. Verify the payment appears in Stripe Dashboard
5. Verify your app receives the payment

STEP 7: Go Live
----------------
1. In Stripe Dashboard, toggle "Test mode" off
2. Use live API keys (sk_live_, pk_live_)
3. Set up real webhook endpoint
4. Money will be deposited to your linked bank account (typically 2-7 day rolling payout)

Pricing Plans (suggested):
--------------------------
- Free: $0/month - basic usage
- Starter: $9.99/month - limited features
- Pro: $29.99/month - full features  
- Enterprise: $99.99/month - priority support

Payouts:
---------
- Stripe sends payouts to your bank account automatically
- Default: daily payouts for balances > $5
- Can configure: daily, weekly, monthly
- First payout typically takes 7 days to verify bank account
