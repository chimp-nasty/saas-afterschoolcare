<script lang="ts">
    import { page } from '$app/state';

    import Authorize from '$lib/auth/Authorize.svelte';

	let { children } = $props();

    // Day-to-day staff screens (/staff/...); admins see them too:
    // docs/staff-platform.md.
    const roles = ["staff", "admin", "superadmin"]
</script>

<Authorize locationCode={page.data.locationCode} {roles}>
    {@render children()}
</Authorize>
