<script lang="ts">
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';

	let { data } = $props();
</script>

<Page>
	<PageHeader title={`Welcome to ${data.location.display_name ?? data.location.location_name}`} />
</Page>