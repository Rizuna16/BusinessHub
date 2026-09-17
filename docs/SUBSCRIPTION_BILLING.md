# Subscription & Platform Billing Foundation

## Overview
Feature #52 introduces the subscription and platform billing foundation for BusinessHub.

## Business Model
- **Plan:** Business Plan (`plan_business_standard`)
- **Price:** Rp50,000.00 IDR / month
- **Billing Interval:** Monthly

## Domain Separation
- **Platform Billing:** Governs SaaS access between Tenant Business and BusinessHub (`Subscription`).
- **Tenant Payment Engine (#32):** Governs customer/supplier transactions inside the tenant business. These two domains are strictly separated.

## Subscription States
- `ACTIVE`
- `PAST_DUE`
- `EXPIRED`
- `CANCELLED`
- `SUSPENDED`

## Controlled Subscription Override
Super Admin can invoke `POST /api/v1/platform/subscriptions/{id}/override` to extend active periods or update subscription status. All overrides require an audit reason and generate immutable audit logs.
