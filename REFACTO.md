REFRACTO STATUS
===============

Architecture context: all apps must follow the rules in `CONTEXT.md`—models split under `app/models/`, read logic in `app/queries/`, write workflows in `app/services/`, views packaged under `app/views/` (HTMX views in `app/views/htmx/`), templates global (eventually fragments under `templates/fragments/<app>/`), and imports must always come through `from <app>.models import ...`.

App Work Summary
----------------

1. **listings**
   - **Done**: Models split under `listings/models/`, services/queries/views reorganized (with `htmx/` split), URLs wired, tests in `listings/tests/{views,queries,services}/`.
   - **Templates to do**: Move HTMX fragments to `templates/fragments/listings/`, relocate any app-level templates under `templates/listings/`.

2. **accounts**
   - **Done**: Models/services/queries/views refactored to match architecture; views packaged.
   - **Templates to do**: Migrate account-specific fragments/templates into the global templates tree.

3. **ai**
   - **Done**: Restructured models/services/queries/views per architecture; cross-imports cleaned.
   - **Templates to do**: Move AI templates/fragments into `templates/`/`templates/fragments/ai/`.

4. **billing**
   - **Done**: Core code refactored to models/services/queries/views packages.
   - **Templates to do**: Consolidate billing-related templates/fragments under the global templates directories.

5. **catalog**
   - **Done**: Catalog app adherence ensured for models/services/queries/views.
   - **Templates to do**: Shift catalog templates/fragments to `templates/` and `templates/fragments/catalog/`.

6. **commerce**
   - **Done**: Commerce models/services/queries/views reorganized.
   - **Templates to do**: Move commerce templates/fragments into `templates/fragments/commerce/`.

7. **ingestion**
   - **Done**: Packaged models/services/queries/views; HTMX views separated.
   - **Templates to do**: Relocate ingestion fragments/templates into global templates tree.

8. **location**
   - **Done**: Services/queries/views reorganized; models kept compliant.
   - **Templates to do**: Transition location templates/fragments to `templates/fragments/location/`.

9. **mediahub**
   - **Done**: Models/services/queries/views restructured.
   - **Templates to do**: Move mediahub fragments/templates under `templates/fragments/mediahub/`.

10. **messaging**
    - **Done**: Refactor to service/query/view packages.
    - **Templates to do**: Globalize messaging templates/fragments.

11. **operations**
    - **Done**: Services/queries/views reorganized; operations HTMX planned.
    - **Templates to do**: Move templates into central templates tree.

12. **reports**
    - **Done**: Initial refactor started; needs completion (models split, views packaged, queries/services wired).
    - **Templates to do**: Once logical refactor complete, move report-related fragments/templates to `templates/fragments/reports/`.

Next Steps
----------
- Complete reports app refactor and ensure its templates eventually conform to the global structure.
- Begin moving each app’s templates/fragments into the shared `templates/` and `templates/fragments/<app>/` directories, starting with HTMX fragments.
