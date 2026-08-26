<script lang="ts">
	import { goto } from '$app/navigation';

	import Button from '$lib/components/actions/Button.svelte';
	import { auth, clearSession } from '$lib/auth/state.svelte';

	const title = "App Name"

	let isLoading = $state(false);

	async function logout() {
		isLoading = true;

		try {
			clearSession();
			await goto('/');
		} finally {
			isLoading = false;
		}
	}
</script>

<header
	class="
		sticky
		top-0
		z-40
		mb-6
		w-full
		border-b
		border-(--border)
		bg-(--surface)/90
		p-4
		backdrop-blur-md
	"
>
	<div class="flex w-full items-center gap-4">
		<p class="mr-auto text-sm font-semibold text-(--text)">
			{title}
		</p>

		{#if $auth.authenticated}
			<p class="text-sm text-(--text-muted)">
				Logged in as {$auth.firstName ?? $auth.email}
			</p>

			<Button
				{isLoading}
				textSize="sm"
				variant="ghost"
				onclick={logout}
			>
				Logout
			</Button>
		{:else}
			<Button
				textSize="sm"
				variant="ghost"
				onclick={() => goto('/login')}
			>
				Login
			</Button>
		{/if}
	</div>
</header>