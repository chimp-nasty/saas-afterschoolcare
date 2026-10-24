<!--
    Platform login: the platform's own admins (not a business's owner or
    staff; they log in on their business's site).
-->
<script lang="ts">
	import { goto, invalidate } from '$app/navigation';

	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import LoginForm from '$lib/features/auth/components/LoginForm.svelte';

	import { createPlatformApi } from '$lib/api/platform/adapters/platform';
	import type { LoginRequest } from '$lib/api/schema';

	const platformApi = createPlatformApi();

	async function login(body: LoginRequest) {
		const response = await platformApi.login(body);

		if (response.ok) {
			await invalidate('app:platform-session');
			await goto('/platform');
		}

		return response;
	}
</script>

<Page>
	<PageHeader title="Platform" description="For the platform's administrators." />

	<LoginForm onsubmit={login} />
</Page>
