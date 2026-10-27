# Frontend patterns: a human overview

We use SvelteKit with Svelte 5, TypeScript and Tailwind. The frontend builds as static files using SvelteKit's static adapter, suitable for AWS CloudFront. Browser requests reach the backend through `/api` on the same site. Sonner (`svelte-sonner`) supplies toast messages.

## Establish the foundation first

Before building features, establish and review basic shared components: Button, ActionBar, Page, PageHeader, Card, Form, Field, error feedback, Modal, Drawer and Authorize. Also agree loading/empty states, navigation links and confirmations. The [portable kit](frontend-portable/) is a neutral starting point, with one basic implementation per building block.

Colours, control styles and other shared choices live centrally. Features use those foundations rather than inventing their own buttons, cards or form fields. This makes style audits useful throughout development: a correction to a shared component propagates to its consumers. Every slice checks that the change still works across affected pages.

Work progresses through sensible stages and small end-to-end slices. The human checks the foundation before feature work and tests/confirms each slice before the agent starts the next.

## Where code lives

| Location | Purpose |
| --- | --- |
| `src/lib/components/` | Shared presentation and local UI state. |
| `src/lib/features/<feature>/components/` | Feature UI built from shared components. |
| `src/lib/api/<domain>/adapters/` | Resource-specific API methods through `createXApi(fetcher)` factories. |
| `src/lib/api/wrapper.ts` | Shared requests, validation-error mapping and mutation toasts. |
| `src/lib/api/schema.ts` | Backend API types, generated and committed. |
| `src/lib/auth/` | Session state, visibility checks and Authorize. |
| `src/routes/` | Loaders, pages, navigation decisions and mutation callbacks. |

Logical domains can align with backend folders and database schemas, such as `auth`, when that helps clarity. A one-to-one match is a recommendation rather than a requirement.

## Pages own data; components display it

Page/layout loaders read data through adapters, passing SvelteKit's fetch function. They declare dependency names such as `app:records`. After a successful save, the page invalidates the relevant dependency so SvelteKit reloads its data.

Forms receive data and a submit callback. They own input values, loading state and field errors; the page calls the adapter and handles refresh/navigation. API adapters and mutation workflows stay out of components. The wrapper supplies consistent responses and Sonner toasts, avoiding repeated request/error handling.

## Access and validation

Roles control sensible page/navigation visibility. Backend-provided permissions control individual actions. Authorize hides UI until session state is known and access is allowed. These checks improve the user experience; the backend's RBAC and database RLS remain authoritative.

The JWT stays in an HttpOnly cookie; browser code reads a safe session endpoint instead. Backend Pydantic models validate input. Frontend forms use native HTML validation plus client-only checks such as password confirmation, then display server field errors.

## Generated files have source owners

`openapi-typescript` reads the backend's OpenAPI description and generates TypeScript API types. It does not make API calls or create data. After backend routes or request/response schemas change, the human regenerates `schema.ts`, runs frontend checks and fixes affected source code. Never edit generated types directly.

Similarly, `sqlacodegen` reads the database schema and generates backend SQLAlchemy models. SQL is the source; generated models are not hand-edited and have no ORM relationships. Repositories write joins explicitly.

The [frontend agent guide](frontend-agent-guide.md) includes step-by-step installation, generation and verification commands for someone unfamiliar with these tools. The [backend guide](backend-agent-guide.md) explains database/model generation. Agents supply commands; the human runs tests and database operations and reports results.

These guides and templates were derived by static inspection. They are not a tested application or a completed CloudFront deployment.
