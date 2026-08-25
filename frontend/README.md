# SvelteKit Frontend Shell

This is an architecture shell, not an initialized SvelteKit project.

Recommended setup:
1. Run `npx sv create` in a clean or temporary directory.
2. Choose the desired SvelteKit/TypeScript options and add Tailwind/Vitest.
3. Merge this shell's `src`, `static`, and `tests` structure into the generated project.
4. Keep the framework-generated package.json, tsconfig.json, svelte.config.js, vite.config.ts and related configuration.

Architecture:
- Components never fetch remote data.
- +page.ts owns initial page loading.
- +page.svelte owns mutations and page orchestration.
- API adapters mirror backend route files.
- API types mirror backend Pydantic schemas.
- Frontend-only types live inside features.
- Shared components are generic UI building blocks only.
- Global state is limited to auth/token state, tenant branding, and toast state.
- Frontend route gating is coarse role-based UX gating; backend permissions are authoritative.
- Tailwind only initially.
- No global domain cache.
- No generic mutation helper initially.
