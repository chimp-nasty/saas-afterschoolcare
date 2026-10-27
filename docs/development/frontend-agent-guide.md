# Frontend development instructions for an agent

Use this contract with the [backend agent guide](backend-agent-guide.md), [human overview](frontend-patterns-overview.md) and [portable frontend kit](frontend-portable/). It generalises the reference frontend without carrying over its domain, branding or navigation.

## Required decisions and operating rules

Use SvelteKit, Svelte 5 runes, TypeScript and Tailwind CSS wherever practical. Always use `@sveltejs/adapter-static` for static output suitable for AWS CloudFront. Do not introduce SvelteKit server routes, server actions, server loaders or a runtime SSR dependency. Application data and authorisation live in the backend. Serve browser API calls on the same origin under `/api`.

Use `svelte-sonner` for toasts, with one root `Toaster`. Keep the existing `createXApi(fetcher)` factory style; these adapters return method objects, not TypeScript classes. Backend API types must be generated with `openapi-typescript`. Never hand-edit or duplicate those wire types. UI-only types are allowed separately.

Never run tests yourself. Never execute commands that touch a database, including starting a backend whose startup checks connect to it. Give the human commands, directories and effects. Do not read environment files or secrets. Do not install packages, generate outputs or claim runtime verification as part of this documentation handoff. In future implementation sessions, preserve the human-run test/database workflow.

Confirm users, roles, permissions, scope, navigation and presentation needs before implementation. Organise work into dependency-ordered stages and small vertical slices. The first stage is the shared foundation; no domain feature may be implemented before it is established, tested by the human and explicitly confirmed. Each later slice has acceptance criteria and stops for human verification/confirmation before the next begins. Fix failures in the current slice first.

## Foundation before features

Ask the user to provide `frontend-portable/` with this guide. Copy template paths into the new `frontend/`, merging root layouts/configuration deliberately rather than overwriting an existing app. These files are source templates, not a complete application/package. Supply package metadata, TypeScript/SvelteKit scaffold and required dependencies. Keep one coherent basic implementation per component; do not create competing button/card systems or speculative style variants.

The neutral kit contains:

| Area | Baseline |
| --- | --- |
| Actions | `Button`, `ActionBar` |
| Layout | `Page`, `PageHeader`, `Card` |
| Forms | `Form`, `Field`, shared submit/error types |
| Text | `ErrorText` |
| Overlays | `Modal`, `Drawer` using native modal dialogs |
| Visibility | `auth/Authorize.svelte` with explicit identity/role/permission props |
| API | `base.ts`, preserved `wrapper.ts` |
| Composition | Root layout with Sonner, client rendering flag, neutral CSS tokens, static adapter and Vite proxy |

Before feature work, also establish a single shared presentation for loading, empty and failed reads, a semantic navigation link, and a confirmation flow for consequential actions. These can be small components, not a large UI framework. Build a foundation showcase route showing field errors, busy/disabled actions, cards, page widths, overlays and toast behaviour. It must use synthetic data and no domain API calls. Human verification covers mobile/desktop, keyboard operation, focus return, Escape, labels/error associations, contrast and layout overflow. Native dialog templates are a starting point, not evidence that accessibility has been tested.

Use Tailwind utilities against centrally defined semantic CSS tokens. Hex colours belong only in the token definition, not individual features. Start with restrained defaults; agree any typography, spacing, radius or theme changes in the foundation stage. Use a single global native-input style. Add component configuration through typed props/snippets for a real reusable need; avoid page-specific class overrides that bypass the foundation. Small scoped CSS is acceptable for browser selectors such as `::backdrop`.

Use semantic HTML, visible focus, labels, adequate contrast, 44px minimum interactive targets and mobile-first layouts. Native controls use 16px text, appropriate input types, inputmode and autocomplete. No required behaviour depends on hover. Keep presentation choices configurable centrally without importing the source project's narrow-customer/wide-admin assumptions.

After each slice, perform a static style audit against the foundation. Give the human showcase and affected-page checks. Fix shared defects in the shared component/token, then inspect all consumers. Do not patch identical style problems independently in pages. A new shared variant must have a demonstrated need and remain consistent with existing consumers. The reference's 'extract after three copies' heuristic does not override the requirement to establish known foundations before features.

## Structure

```text
frontend/
  src/
    lib/
      api/
        schema.ts                  # generated and committed
        base.ts
        wrapper.ts
        <domain>/adapters/<resource>.ts
      auth/                        # session state, Authorize, permission helpers
      components/
        actions/
        forms/
        layout/
        overlays/
        text/
        feedback/
      features/<feature>/
        components/
        types.ts                   # UI-only types when needed
      navigation/                  # shared route/menu/tab definitions
      types/forms.ts
      utils/                       # shared formatting/helpers
    routes/
      +layout.ts
      +layout.svelte
      layout.css
      <route>/+page.ts
      <route>/+page.svelte
  static/
```

Group API adapters by logical backend domain. Aligning frontend domains, backend domains and PostgreSQL schemas is recommended when it makes ownership clear: `auth` is a useful example. This is not a mandatory one-to-one mapping, and does not mean exposing database models directly as API types. Choose route groups and feature folders around user journeys without copying tenant/platform/kiosk structures into every project.

Shared components own presentation and local UI state, with no API calls or business workflows. Feature components combine those blocks and accept typed data/callbacks. Routes own API orchestration, navigation and invalidation. Do not import adapters, fetch business data or define mutation workflows in shared or feature components. Even a reused widget should receive its data and callbacks from its route/controller boundary.

## API wrapper and factories

Copy `src/lib/api/wrapper.ts` from the portable kit. It is the reference wrapper unchanged: same-origin credentialed fetch; JSON, FormData and URL-encoded bodies; injected fetch; consistent client response including HTTP `status` and `fieldErrors`; 422 field mapping; network-error results; non-GET Sonner toasts; `quiet` and `silent` controls. The comments' example contexts are illustrative, not features to implement. `ApiResponse<T>` here is a local transport/result helper enriched with client-only fields; it does not replace generated backend payload types.

Do not duplicate success/error toasts at call sites. GET failures need explicit page error handling because the wrapper does not toast reads. `quiet` suppresses success toasts; `silent` suppresses all toasts. Neither substitutes for reporting failures in the UI. Do not set multipart Content-Type manually. The wrapper uses TypeScript assertions, not runtime payload validation. It also catches exceptions from `onSuccess` as network errors, so keep navigation/invalidation in page callbacks rather than that hook. Non-JSON successful responses produce null data: typed domain reads must check for expected data and cannot assume HTTP success means valid payload.

One adapter per backend resource router encapsulates URLs, methods, bodies and query encoding. Example only, after the generated schema contains these names:

```ts
import { API_BASE } from '$lib/api/base';
import { apiWrapper } from '$lib/api/wrapper';
import type { RecordResponse, UpdateRecordRequest } from '$lib/api/schema';

export function createRecordsApi(fetcher?: typeof fetch) {
  const base = `${API_BASE}/records/v1`;
  return {
    list: () => apiWrapper<RecordResponse[]>(`${base}/`, { fetcher }),
    update: (id: string, body: UpdateRecordRequest) =>
      apiWrapper<RecordResponse>(`${base}/${encodeURIComponent(id)}`, {
        method: 'PATCH', body, fetcher
      })
  };
}
```

Import request/response types from generated `schema.ts`. Derive query/filter types from generated `operations[operationId]['parameters']['query']`; use generated enum value arrays for dropdowns where available. Do not manually restate backend enumerations. Keep form view state and other client-only models in feature/type modules.

## Loaders, pages and forms

Read in universal `+page.ts` / `+layout.ts` loaders. Pass SvelteKit's provided `fetch` into the factory and declare semantic dependency keys. Share stable session/navigation reads in a suitable layout; load resource data in the page that owns it. Example:

```ts
import type { PageLoad } from './$types';
import { createRecordsApi } from '$lib/api/public/adapters/records';

export const load: PageLoad = async ({ fetch, depends }) => {
  depends('app:records');
  const response = await createRecordsApi(fetch).list();
  return { records: response.data ?? [], loadError: response.ok ? null : response.msg };
};
```

Render read failures distinctly from empty data; use loader redirects/errors when the user journey requires them. After a successful mutation, a page callback runs `await invalidate('app:records')` for affected reads and navigates when needed. Invalidate related layout/session keys if their data changed. Avoid indiscriminate `invalidateAll()` and optimistic state that disagrees with the confirmed server result. React to new page data with `$derived`, rather than copying it into permanent initial state.

The page constructs the adapter, calls its mutation method, handles success/invalidation and returns the response to the form. The form receives `onsubmit: SubmitHandler<GeneratedRequest>`, owns editable body/loading/errors, prevents duplicate submission, and displays returned field errors. Reset only when appropriate to the workflow and after success. For edits, initialise from typed data; preserve user input on failure. Always release loading state with `finally`.

Use `Field` around native controls. This kit passes a snippet object containing `id`, `aria-describedby` and `aria-invalid`; spread it onto the control to associate errors. `Form` handles submission shell/loading; it does not call adapters. Backend Pydantic validation is authoritative. Use HTML required/type/length constraints and client-only cross-field checks such as password confirmation; avoid reproducing backend business rules.

## Session and frontend visibility

Use roles for sensible page/navigation groupings and backend-provided effective permissions for individual actions. Create session bootstrap, role/permission helpers and route/layout guards after the domain is known. Read session information from a backend endpoint using the HttpOnly cookie; do not read/store the JWT in JavaScript or localStorage. Session response types must also be generated. Refresh session data after login, logout or scope/role changes as appropriate, and handle 401/403 coherently.

Do not show protected content while session state is uninitialised. `Authorize` handles UI visibility with props; it intentionally has no hard-coded scope, auth store or redirect path. A page/layout chooses unauthenticated/forbidden redirects and passes state. Permission checks must use the relevant scope's map and fail closed. Frontend checks improve usability; users can bypass them. Backend router RBAC and database RLS enforce security on every operation. No protected data belongs in static output.

## Mandatory generated types: human walkthrough

Explain this before asking the human to generate anything: `openapi-typescript` reads the backend's OpenAPI JSON contract and writes TypeScript descriptions of endpoints, request bodies and responses. It does not fetch application records or implement an API client. Adapters still make requests. TypeScript catches incompatible call sites when the contract changes.

Configure a pinned compatible `openapi-typescript` development dependency in `frontend/package.json`, plus scripts (the reference uses version 7.13.0; select/verify compatibility in a new project):

```json
{
  "scripts": {
    "gen:api": "openapi-typescript http://localhost:8000/openapi.json -o src/lib/api/schema.ts --root-types --root-types-no-schema-prefix --enum-values",
    "gen:api:file": "openapi-typescript ./.openapi.json -o src/lib/api/schema.ts --root-types --root-types-no-schema-prefix --enum-values",
    "check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json",
    "build": "vite build"
  }
}
```

Human steps:

1. Install the project's declared dependencies in `frontend/` using `npm install`. This downloads dependencies and updates local package/install artifacts. Commit the intended package manifest/lockfile.
2. After a backend route or Pydantic schema change, update the backend first. If SQL changed, follow the backend guide's human-run dev rebuild/model-generation steps first.
3. For URL generation, the human starts the configured development backend from `backend/`, for example `./venv/Scripts/python -m uvicorn app.main:app --reload --port 8000`. Startup connects to the configured database to check the runtime role; verify the development target first. In a second terminal, run `npm run gen:api` from `frontend/`. This reads `/openapi.json` and overwrites `src/lib/api/schema.ts`.
4. Alternatively, the human exports OpenAPI without starting the server, from `backend/`: `./venv/Scripts/python -c "import json; from pathlib import Path; from app.main import app; Path('../frontend/.openapi.json').write_text(json.dumps(app.openapi()), encoding='utf-8')"`. This imports the configured application and writes a local JSON file; it is intended not to run lifespan/database operations. Verify the new app's import behaviour before using it. Then run `npm run gen:api:file` from `frontend/`. The retained dev migrator also attempts this generation hook when configured.
5. Run `npm run check` in `frontend/`; fix reported adapter/form/page mismatches in source, then repeat generation/checks as needed. Run `npm run build` to check static output. These commands generate local artifacts; the human runs them in this workflow. Commit `schema.ts`; keep `.openapi.json` transient/ignored unless a project explicitly versions its contract.

Never edit generated `schema.ts` to make an error disappear. Change the backend contract if wrong, or adapt frontend source if the contract is correct, then regenerate. Generated API types, SvelteKit's generated `./$types`, and UI-only types have distinct owners. Generation success is not proof the API works; runtime tests remain necessary.

## Static hosting and verification

The kit uses conventional `svelte.config.js` for `adapter-static({ fallback: 'index.html' })`, and `vite.config.ts` for Tailwind/SvelteKit plugins and `/api` proxy. The source project configures the adapter inside its Vite SvelteKit plugin; do not configure it twice in a new project. Root `ssr=false` gives browser rendering. Keep private/dynamic routes out of prerendered data. Any prerender policy must be deliberate.

CloudFront serves generated static assets and sends `/api/*` to the AWS-hosted backend, preserving the required host/cookie/origin contract and disabling API caching for authenticated responses. Deep links must reach the SPA fallback for page requests; do not rewrite API errors or missing JS/CSS assets to HTML. Test refresh on nested routes. Do not put secrets in frontend environment variables or the bundle. Infrastructure creation is a separate task.

Each handoff includes focused unit/component/browser tests for relevant behaviour and exact human commands. Typical frontend commands, from `frontend/`, after scripts/dependencies exist: `npm run check`, `npm run build`, `npm run test:unit -- --run`, and `npm run test:e2e`. Explain browser installation/download requirements; do not hide them in a test script. Real API end-to-end tests need the isolated test backend/Neon branch and faked external services, never production. Keep mocked UI tests distinct from real integration evidence.

Each slice checks generated-type compatibility, loading/error/empty states, validation, keyboard/mobile behaviour, role/permission visibility, successful mutation invalidation and shared-style consistency. Stop for the human's results and confirmation before the next slice. Do not claim the portable kit is tested: it was statically inspected only.

## Source and limits

Based on static inspection on 2026-10-27 of `frontend/CLAUDE.md`, package scripts, Vite configuration, root layouts, API wrapper, representative factory adapter, settings loader/page, auth state/Authorize, form types and shared components. No environment files were read, tests/checks/builds were run or dependencies installed. Wrapper/form types were copied; foundation components and static configuration are deliberately simplified templates. Backend integrations and deployment implementation were excluded.
