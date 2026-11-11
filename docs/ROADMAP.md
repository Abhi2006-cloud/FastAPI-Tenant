# Product Roadmap & Out-of-Scope Architecture

This document outlines future features, deferred integrations, and out-of-scope capabilities for the **AI Workspace SaaS Backend**.

---

## 1. Out-of-Scope in Current Zero-Cost Free-Tier Phase

The following capabilities are deliberately excluded from the current phase to satisfy the zero-cost, credit-card-free deployment constraint:

### 💳 Stripe & Payment Gateways
- **Current Architecture**: Upgrade requests are created via `POST /organizations/{org_id}/upgrade-request` and approved by platform administrators via `PATCH /admin/organizations/{org_id}/plan`.
- **Reason**: Payment processors require external merchant accounts, live API keys, and webhook signing secrets.
- **Future Plan**: Integrate Stripe Checkout and Billing Portal with idempotency-key handling and automated plan synchronization upon webhook verification.

### 🏢 Enterprise SSO & SAML
- **Current Architecture**: Password-based bcrypt authentication with JWT session rotation and Redis revocation.
- **Reason**: SAML / OIDC IdP integrations (Okta, Azure AD, Google Workspace SAML) require enterprise infrastructure setups.
- **Future Plan**: Add standard SAML 2.0 and OIDC identity federation with organization-level domain claiming (`sso_domain`).

### 🪝 Outbound Webhooks & Event Subscriptions
- **Current Architecture**: Audit logs and events are persisted to PostgreSQL and indexed in background queues.
- **Reason**: Outbound HTTP webhooks introduce retry queues, dead-letter storage, and potential egress bandwidth costs.
- **Future Plan**: Add HMAC-signed webhook delivery for tenant lifecycle events (`member.joined`, `file.uploaded`, `plan.changed`).

### 🌐 Object Storage (AWS S3 / Cloudflare R2)
- **Current Architecture**: Pluggable storage abstraction with PostgreSQL `file_blobs` (`BYTEA`) backend for persistent files on ephemeral containers.
- **Reason**: Cloudflare R2 and AWS S3 require credit cards or external accounts.
- **Future Plan**: Add S3-compatible presigned URL uploads when cloud storage accounts are linked.

### 🌍 Multi-Region Replication
- **Current Architecture**: Single-region serverless PostgreSQL (Neon) and serverless Redis (Upstash).
- **Reason**: Multi-region active-active database replication exceeds free-tier resource bounds.

---

## 2. Planned Roadmap Milestones

| Milestone | Target Capability | Target Tier |
| :--- | :--- | :--- |
| **v2.6.0** | Interactive React 19 Frontend with Entitlements & Demo UI | Zero-Cost Free Tier |
| **v2.7.0** | Automated Organization Data Export (GDPR compliant ZIP bundle) | Free Tier |
| **v3.0.0** | Stripe Billing Webhook Integration & Automated Invoicing | Paid Extension |
| **v3.1.0** | WorkOS / Auth0 Enterprise SSO & SCIM Directory Sync | Enterprise |
| **v3.2.0** | S3 / R2 Multipart Direct-to-Storage Presigned Uploads | Pro & Enterprise |

