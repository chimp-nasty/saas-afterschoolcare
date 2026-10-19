<script lang="ts">
    import { page } from '$app/state';

    import Authorize from '$lib/auth/Authorize.svelte';

	let { children } = $props();

    // Any role, but a role is required.
    const roles = ["customer", "staff", "admin", "superadmin"]
</script>

<Authorize locationCode={page.data.locationCode} {roles}>
    {@render children()}
</Authorize>