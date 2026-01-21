## Architecture rules (STRICT)

### 1) Models
- Models are “pure”: only fields, Meta, __str__, and light read-only helpers.
- NO business logic, NO DB writes, NO side effects in models.
- Models are split into submodules under app/models/.
- models/__init__.py re-exports all public models.

### 2) Services
- All write operations (create/update/delete), workflows, and transactions MUST live in app/services/.
- Services can raise domain exceptions.
- Services are the only place allowed to call save(), update(), create().
- Views must call services, never write to DB directly.

### 3) Queries
- Read-only DB access (QuerySets, filters, annotations) live in app/queries/.
- Queries must never write to DB.
- Queries return QuerySets or lists, not HttpResponses.

### 4) Views 
- Views MUST live in app/views/ as a Python package (directory).
- A single views.py file is FORBIDDEN.
- app/views/__init__.py must exist and re-export public views if needed.
- Views are thin controllers only.
- Views orchestrate services + queries and pass data to templates.
- NO business logic, NO DB writes, NO complex conditionals.
- HTMX views MUST be isolated (e.g. app/views/htmx/).

### 5) Templates
- Templates are global (single templates/ directory).
- HTML partials go under templates/fragments/.
- HTMX is used heavily; fragments must be reusable.

### 6) Naming conventions
- Use explicit domain naming (listing, offer, alert).
- Avoid generic names like utils.py or helpers.py.
- Use snake_case filenames.

### 7) Imports
- Always import models from app.models (never from submodules directly).
  Example: `from listings.models import Listing, Offer`
- Views must import services from app.services and queries from app.queries.

### 8) Transactions
- Services modifying multiple models MUST be wrapped in atomic transactions.

### Compliance rule
If a request would violate these rules, propose a compliant alternative
instead of generating incorrect code.
