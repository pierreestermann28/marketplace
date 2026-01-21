REFRACTO STATUS
===============

Architecture context: all apps must follow the rules in `CONTEXT.md`—models split under `app/models/`, read logic in `app/queries/`, write workflows in `app/services/`, views packaged under `app/views/` (HTMX views in `app/views/htmx/`), templates global (eventually fragments under `templates/fragments/<app>/`), and imports must always come through `from <app>.models import ...`.

App Work Summary
----------------

1. **listings**
   - **Done**: Models split under `listings/models/`, services/queries/views reorganized (with `htmx/` split), URLs wired, tests in `listings/tests/{views,queries,services}/`.
   - **Templates to do**: Completed — moved listing pages into `templates/listings/`, fragments remain under `templates/fragments/listings/`.

2. **accounts**
   - **Done**: Models/services/queries/views refactored to match architecture; views packaged; account templates already under `templates/accounts/`.
   - **Templates to do**: None remaining (global templates already in place).

3. **ai**
   - **Done**: Restructured models/services/queries/views per architecture; cross-imports cleaned.
   - **Templates to do**: None (no AI-specific pages/fragments exist yet).

4. **billing**
   - **Done**: Core code refactored to models/services/queries/views packages.
   - **Templates to do**: None (no billing templates currently exist).

5. **catalog**
   - **Done**: Catalog app adherence ensured for models/services/queries/views.
   - **Templates to do**: None (no catalog templates currently exist).

6. **commerce**
   - **Done**: Commerce models/services/queries/views reorganized.
   - **Templates to do**: None (commerce uses only shared templates for now).

7. **ingestion**
   - **Done**: Packaged models/services/queries/views; HTMX views separated.
   - **Templates to do**: None (already in `templates/ingestion/` + `templates/fragments/ingestion/`).

8. **location**
   - **Done**: Services/queries/views reorganized; models kept compliant.
   - **Templates to do**: None (uses only shared components/templates already compliant).

9. **mediahub**
   - **Done**: Models/services/queries/views restructured.
   - **Templates to do**: None (no mediahub templates yet).

10. **messaging**
    - **Done**: Refactor to service/query/view packages.
    - **Templates to do**: None (already under `templates/messaging/` and `templates/messaging/partials/`).

11. **operations**
    - **Done**: Services/queries/views reorganized; operations HTMX planned.
    - **Templates to do**: None (templates already live under `templates/operations/`).

12. **reports**
    - **Done**: Initial refactor started; needs completion (models split, views packaged, queries/services wired).
    - **Templates to do**: None for now (only `templates/components/reports/` in use); will relocate fragments once app UI expands.

Next Steps
----------
- Complete reports app refactor and ensure its templates eventually conform to the global structure.
- Begin moving each app’s templates/fragments into the shared `templates/` and `templates/fragments/<app>/` directories, starting with HTMX fragments.
