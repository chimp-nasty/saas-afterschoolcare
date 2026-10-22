<!--
    The account page's Profile tab: your contact details, your emergency
    contact (both needed before booking), then changing your password,
    stacked (the tabs stay at three).
-->
<script lang="ts">
	import Notice from '$lib/components/text/Notice.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';
	import EmergencyContactForm from '$lib/features/customer/components/EmergencyContactForm.svelte';
	import ParentProfileForm from '$lib/features/customer/components/ParentProfileForm.svelte';
	import ChangePasswordForm from '$lib/features/account/components/ChangePasswordForm.svelte';

	import type {
		ChangePasswordRequest,
		CustomerProfileResponse,
		UpdateCustomerProfileRequest
	} from '$lib/api/schema';
	import type { SubmitHandler } from '$lib/types/forms';
	import { hasEmergencyContact } from '../emergency';

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
		<SectionHeading title="Your details" />

		<ParentProfileForm {profile} {onsubmit} />
	</section>

	<section class="flex flex-col gap-3">
		<SectionHeading
			title="Emergency contact"
			description="Someone we can call if we can't reach you. They can't collect your children unless they're also on your pickup list."
		/>

		{#if !hasEmergencyContact(profile)}
			<Notice tone="warning">Add an emergency contact before booking.</Notice>
		{/if}

		<EmergencyContactForm {profile} {onsubmit} />
	</section>

	<section class="flex flex-col gap-3">
		<SectionHeading title="Change password" />

		<ChangePasswordForm onsubmit={onchangepassword} />
	</section>
</div>
