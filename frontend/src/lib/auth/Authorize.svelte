<script lang="ts">
	import { goto } from '$app/navigation';
	import type { Snippet } from 'svelte';

	import { auth } from '$lib/auth/state.svelte';

	type Props = {
		locationCode: string;
		roles: string[];
		children: Snippet;
		fallback?: Snippet;
		redirect?: boolean;
	};

	let {
		locationCode,
		roles,
		children,
		fallback,
		redirect = true
	}: Props = $props();

	const authorized = $derived(
		$auth.authenticated &&
		roles.some((role) => $auth.roles.includes(role))
	);

	$effect(() => {
		if ($auth.initialized && !authorized && redirect) {
			void goto(`/${locationCode}`);
		}
	});
</script>

{#if authorized}
	{@render children()}
{:else if !redirect && fallback}
	{@render fallback()}
{/if}