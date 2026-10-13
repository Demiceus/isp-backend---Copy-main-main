# NetAssist AI — Professional UI

## Customer experience
- `index.html` — public marketing / support landing page
- `customer.html` — customer support chat portal

## Admin experience
- `admin-login.html` — local UI gate for the admin console
- `admin-dashboard.html` — glassmorphism operations dashboard with bento-style analytics
- `admin-escalations.html` — escalation triage and case detail workspace

## Backend addition
- `GET /api/admin/analytics` — dashboard-ready metrics, 7-day session trend, sentiment mix, and complaint categories.

## Run
1. Start the Flask API as usual.
2. Serve `netassist-frontend/` from a local/static web server rather than opening HTML directly from `file://`.
3. Open `index.html` for customers.
4. Open `admin-login.html` for the operations console.

## Important
The admin login is currently a presentation-layer gate only. The existing backend does not expose authentication/authorization, so production deployment should add real admin authentication, role-based access control, CSRF protection, secure cookies/tokens, and HTTPS before exposing the admin console publicly.
