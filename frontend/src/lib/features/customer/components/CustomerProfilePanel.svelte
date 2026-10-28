<!--
    The account page's Profile tab: your contact details and your emergency
    contact (both needed before booking), stacked. Changing your password is
    in Account settings.
-->
<script lang="ts">
	import Notice from '$lib/components/text/Notice.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';
	import EmergencyContactForm from '$lib/features/customer/components/EmergencyContactForm.svelte';
	import ParentProfileForm from '$lib/features/customer/components/ParentProfileForm.svelte';

	import type { CustomerProfileResponse, UpdateCustomerProfileRequest } from '$lib/api/schema';
	import type { SubmitHandler } from '$lib/types/forms';
	import { hasEmergencyContact } from '../emergency';

	let {
		profile,
		onsubmit
	}: {
		profile: CustomerProfileResponse;
		onsubmit: SubmitHandler<UpdateCustomerProfileRequest>;
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
</div>
