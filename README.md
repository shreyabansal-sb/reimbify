# Reimbify — Reimbursements Redefined

> Built for the **Smart Campus Hackathon 2026** at South Asian University (9–10 April 2026)  
> Team Technica · Finalists

Reimbify is a web-based Unified Reimbursement Management System that digitalises the entire expense lifecycle for students, clubs, and university finance departments — replacing manual, paper-based workflows with a transparent, automated platform.

---

## The Problem

University reimbursement processes are broken. Students face delayed reimbursements, confusing approval chains, and no visibility into their remaining budget. Admins deal with stacks of physical bills, inconsistent submissions, and zero audit trail.

Reimbify fixes that.

---

## What It Does

Three portals, one platform:

**Student / Club portal**
- Submit reimbursement requests with bill/receipt upload (image or PDF)
- Request advance funds before spending, then settle afterwards with actual spend
- Track all request statuses in real time with admin comments visible
- Live budget dashboard — allocated vs. used vs. remaining, per category
- 80% budget alert banner to prevent overspend before it happens

**Admin portal**
- Review, approve, reject, or request modifications on all submissions
- Leave comments explaining decisions (visible to student)
- Full request history across all users

**Finance dashboard**
- Live overview of total allocated, spent, and remaining funds
- Budget vs. actual spend charts by category
- Department-wise breakdowns and at-risk budget alerts
- Complete audit trail of every admin action

---

## Special Features

**Budget guardrails** — real-time alerts when a student hits 80% of their allocated budget.

**Auto policy validation** — claims are automatically checked against university spending limits before reaching the admin. Invalid submissions are rejected instantly with a clear reason shown to the student.

Policy limits (students): ₹5,000/claim · ₹2,000 hospitality · ₹3,000 logistics  
Policy limits (clubs): ₹25,000/claim · ₹15,000 hospitality · ₹10,000 logistics

**Google Vision API bill scanning** — uploaded bills are processed to auto-extract amount, vendor, and date. Falls back to manual entry if extraction fails.

**Advance settlement workflow** — students can request funds before spending, then reconcile actual spend vs. advance received. System calculates and records the balance returned.

**JSON API endpoints** — live dashboard updates without full page reloads.

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python + Flask |
| Database | SQLite (dev) / MySQL (production-ready) |
| Frontend | HTML5, CSS3, JavaScript + Jinja2 templates |
| OCR / Bill scanning | Google Cloud Vision API |
| Authentication | Flask sessions (server-side, role-based) |
| File uploads | Werkzeug secure file handling |
| Deployment | Render-ready |

---

## Database Schema

6 tables, auto-created on first run via `init_db()`:

| Table | Purpose |
|---|---|
| `users` | All users (students, clubs, admins) with role-based access |
| `budgets` | Per-user, per-category budget allocation and usage |
| `requests` | Every reimbursement and advance claim |
| `bills` | Uploaded receipts linked to requests, with OCR extraction data |
| `advance_settlements` | Reconciliation records for settled advances |
| `audit_log` | Immutable record of every admin action for compliance |

---

## Project Structure

```
reimbify/
├── app.py               # Main Flask app — all routes, policy checks, session handling
├── database.py          # All DB functions: auth, budgets, requests, bills, analytics, audit
├── schema.sql           # Complete schema with all 6 tables and sample data
├── sample.sql           # Seed data for demo
├── requirements.txt     # Python dependencies
├── templates/
│   ├── student/         # Student portal views
│   ├── club/            # Club portal views
│   └── admin/           # Admin portal views
└── static/
    ├── css/
    ├── js/
    └── uploads/         # Uploaded bill images
```

---

## Team Technica

| Name | Role |
|---|---|
| Shreya Bansal | Backend, system design, project lead |
| Srija Das | Backend |
| Bhavika Pande | Frontend |
| Asavari Nautiyal | Frontend |

---

## Hackathon Context
Built for the Smart Campus Hackathon 2026, South Asian University, 9–10 April 2026.
Problem statement: Unified Reimbursement Management System.
Team Technica was selected as a finalist from among all submitted proposals.

Built for the Smart Campus Hackathon 2026, South Asian University, 9–10 April 2026.  
Problem statement: *Unified Reimbursement Management System* (Challenge I).  
Team Technica was selected as a finalist from among all submitted proposals.
