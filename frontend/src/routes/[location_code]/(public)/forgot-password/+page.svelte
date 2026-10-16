<script lang="ts">
	import ForgotPasswordForm from '$lib/features/auth/components/ForgotPasswordForm.svelte';

	import { createAuthApi } from '$lib/api/auth/adapters/auth';

	const authApi = createAuthApi();
</script>

<ForgotPasswordForm onsubmit={(body) => authApi.forgotPassword(body)} />
