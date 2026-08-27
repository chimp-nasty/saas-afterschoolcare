<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';

	import Button from '$lib/components/actions/Button.svelte';
	import { auth, clearSession } from '$lib/auth/state.svelte';
	import { createAuthApi } from '$lib/api/auth/adapters/auth';

	const title = "App Name"

	let isLoading = $state(false);

	async function logout() {
		isLoading = true;

		try {
			const authApi = createAuthApi(page.params.location_code ?? '');
			await authApi.logout();

			clearSession();
			await goto(`/${page.params.location_code}/`);
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
				onclick={() => goto(`/${page.params.location_code}/login`)}
			>
				Login
			</Button>
		{/if}
	</div>
</header>