<script lang="ts">
    import { page } from '$app/state';

    import Authorize from '$lib/auth/Authorize.svelte';

	let { children } = $props();

    const roles = ["customer"]
</script>

<Authorize locationCode={page.data.locationCode} {roles}>
    {@render children()}
</Authorize>