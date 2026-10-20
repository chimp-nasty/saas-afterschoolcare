<script lang="ts">
    import { page } from '$app/state';

    import Authorize from '$lib/auth/Authorize.svelte';

	let { children } = $props();

    // Location configuration (/admin/...): docs/staff-platform.md.
    const roles = ["admin", "superadmin"]
</script>

<Authorize locationCode={page.data.locationCode} {roles}>
    {@render children()}
</Authorize>
