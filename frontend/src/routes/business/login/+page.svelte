<!--
    Business settings login: the business's owner, with no centre. Anyone
    else is refused as if the password were wrong. Not linked from the
    public site; owners also reach it from their account menu at a centre.
-->
<script lang="ts">
	import { goto, invalidate } from '$app/navigation';

	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import LoginForm from '$lib/features/auth/components/LoginForm.svelte';

	import { createAuthApi } from '$lib/api/auth/adapters/auth';
	import type { LoginRequest } from '$lib/api/schema';

	const authApi = createAuthApi();

	async function login(body: LoginRequest) {
		const response = await authApi.businessLogin(body);

		if (response.ok) {
			await invalidate('app:session');
			await goto('/business');
		}

		return response;
	}
</script>

<Page>
	<PageHeader title="Business settings" description="For the business's owner." />

	<LoginForm onsubmit={login} />
</Page>
