<script lang="ts">
	import { page } from '$app/state';
	import { goto, invalidate } from '$app/navigation';
	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import LoginForm from '$lib/features/auth/components/LoginForm.svelte';

	import { createAuthApi } from '$lib/api/auth/adapters/auth';
	import { markJustLoggedIn } from '$lib/features/actions/loginNotice';
	import type { LoginRequest } from '$lib/api/schema';

	const authApi = createAuthApi();

	async function login(body: LoginRequest) {
		const response = await authApi.login(page.data.locationCode, body);

		if (response.ok) {
			await invalidate('app:session');
			await invalidate('app:actions-count');

			// Home tells them about any messages they haven't seen.
			markJustLoggedIn();

			await goto(`/${page.data.locationCode}/home`);
		}

		return response;
	}
</script>

<Page>
	<PageHeader title="Log in" />

	<LoginForm onsubmit={login} />

	<div class="flex flex-col items-center">
		<HyperTextLink href={`/${page.data.locationCode}/forgot-password`}>
			Forgot your password?
		</HyperTextLink>

		<p class="text-sm text-(--text-muted)">
			New here?
			<HyperTextLink href={`/${page.data.locationCode}/register`}>
				Create an account
			</HyperTextLink>
		</p>
	</div>
</Page>
