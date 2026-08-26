<script lang="ts">
	import { goto } from '$app/navigation';
	import type { Snippet } from 'svelte';

	import { auth } from '$lib/auth/state.svelte';

	type Props = {
		roles: string[];
		children: Snippet;
		fallback?: Snippet;
		redirect?: boolean;
	};

	let {
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
		if (!authorized && redirect) {
			void goto('/');
		}
	});
</script>

{#if authorized}
	{@render children()}
{:else if !redirect && fallback}
	{@render fallback()}
{/if}