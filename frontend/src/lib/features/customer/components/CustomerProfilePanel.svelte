<!--
    The account page's Profile tab: your contact details, then changing
    your password, stacked (the tabs stay at three).
-->
<script lang="ts">
	import ParentProfileForm from '$lib/features/customer/components/ParentProfileForm.svelte';
	import ChangePasswordForm from '$lib/features/account/components/ChangePasswordForm.svelte';

	import type {
		ChangePasswordRequest,
		CustomerProfileResponse,
		UpdateCustomerProfileRequest
	} from '$lib/api/schema';
	import type { SubmitHandler } from '$lib/types/forms';

	let {
		profile,
		onsubmit,
		onchangepassword
	}: {
		profile: CustomerProfileResponse;
		onsubmit: SubmitHandler<UpdateCustomerProfileRequest>;
		onchangepassword: SubmitHandler<ChangePasswordRequest>;
	} = $props();
</script>

<div class="flex flex-col gap-6">
	<section class="flex flex-col gap-3">
		<h2 class="text-lg font-extrabold text-(--text)">Your details</h2>

		<ParentProfileForm {profile} {onsubmit} />
	</section>

	<section class="flex flex-col gap-3">
		<h2 class="text-lg font-extrabold text-(--text)">Change password</h2>

		<ChangePasswordForm onsubmit={onchangepassword} />
	</section>
</div>
