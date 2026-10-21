<script lang="ts">
    import { page } from '$app/state';

    import Authorize from '$lib/auth/Authorize.svelte';

	let { children } = $props();

    // The staff portal (/staff/...): every employee's own account, nothing
    // about children or families (docs/portals.md).
    const roles = ["staff", "admin", "superadmin"]
</script>

<Authorize locationCode={page.data.locationCode} {roles}>
    {@render children()}
</Authorize>
