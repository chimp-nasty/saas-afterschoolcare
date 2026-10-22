<!--
    A family's Details tab in Admin › Families: the parent's phone and
    address (correctable), their emergency contact (read-only: only the
    family changes it), their children with medical status (read-only;
    families manage their children), and their pickup people with ID status
    (read-only; ID checks happen at the staff kiosk).
-->
<script lang="ts">
	import GridTable from '$lib/components/layout/GridTable.svelte';
	import LabelValueList from '$lib/components/text/LabelValueList.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';
	import ParentProfileForm from '$lib/features/customer/components/ParentProfileForm.svelte';
	import PickupIdPill from '$lib/features/kiosk/components/PickupIdPill.svelte';

	import type { CustomerProfileResponse, FamilyResponse, UpdateContactDetailsRequest } from '$lib/api/schema';
	import { emergencyRelationLabel } from '$lib/features/customer/emergency';
	import { STAFF_REVIEW_STATUS_LABELS } from '$lib/features/medical-reviews/status';
	import type { SubmitHandler } from '$lib/types/forms';
	import { formatDate, formatEnum, formatPhone } from '$lib/utils/helpers';

	let {
		family,
		locationCode,
		onsubmit
	}: {
		family: FamilyResponse;
		locationCode: string;
		onsubmit: SubmitHandler<UpdateContactDetailsRequest>;
	} = $props();

	// The profile form edits the same fields families edit on their account.
	const profile = $derived({
		id: family.user_id,
		user_id: family.user_id,
		phone: family.phone,
		address_line_1: family.address_line_1,
		address_line_2: family.address_line_2,
		suburb: family.suburb,
		state: family.state,
		postcode: family.postcode,
		updated_at: ''
	} as CustomerProfileResponse);
</script>

<div class="flex flex-col gap-6">
	<section class="flex flex-col gap-3">
		<SectionHeading
			title="Contact details"
			description="Changing the phone also changes the parent's own place on their pickup list, so staff check their ID again at the kiosk."
		/>
		{#key family.user_id}
			<ParentProfileForm {profile} {onsubmit} />
		{/key}
	</section>

	<section class="flex flex-col gap-3">
		<SectionHeading title="Emergency contact" description="The family keeps this up to date. It doesn't let this person collect the children." />
		<LabelValueList
			columns={3}
			items={[
				{ label: 'Name', value: family.emergency_contact_name },
				{ label: 'Phone', value: family.emergency_contact_phone ? formatPhone(family.emergency_contact_phone) : null },
				{ label: 'Relationship', value: family.emergency_contact_relation ? emergencyRelationLabel(family) : null }
			]}
		/>
	</section>

	<section class="flex flex-col gap-3">
		<SectionHeading title="Children" />
		<GridTable
			items={family.children}
			key={(child) => child.id}
			columns="minmax(10rem,1.5fr) minmax(8rem,1fr) 7rem minmax(10rem,1.3fr) 7rem"
			headers={['Child', 'Date of birth', 'Status', 'Medical', '']}
			label="Children"
			empty="No children yet."
		>
			{#snippet row(child)}
				<span class="text-base font-semibold text-(--text)" role="cell">{child.first_name} {child.last_name}</span>
				<span class="text-base text-(--text)" role="cell">{formatDate(child.dob)}</span>
				<span class="text-base text-(--text)" role="cell">{child.is_active ? 'Current' : 'Removed'}</span>
				<span class="text-base text-(--text)" role="cell">{STAFF_REVIEW_STATUS_LABELS[child.review_status]}</span>
				<span class="text-base" role="cell">
					{#if child.review_status !== 'not_required'}
						<a class="text-(--hyperlink) underline" href={`/${locationCode}/admin/reviews/${child.id}`}>Review</a>
					{/if}
				</span>
			{/snippet}
		</GridTable>
	</section>

	<section class="flex flex-col gap-3">
		<SectionHeading title="Pickup people" />
		<GridTable
			items={family.pickups}
			key={(person) => person.pickup_person_id}
			columns="minmax(10rem,1.5fr) minmax(8rem,1fr) minmax(8rem,1fr) minmax(12rem,1.4fr)"
			headers={['Name', 'Relationship', 'Phone', 'ID']}
			label="Pickup people"
			empty="No pickup people."
		>
			{#snippet row(person)}
				<span class="text-base font-semibold text-(--text)" role="cell">{person.first_name} {person.last_name}</span>
				<span class="text-base text-(--text)" role="cell">{formatEnum(person.relation)}</span>
				<span class="text-base text-(--text)" role="cell">{formatPhone(person.phone)}</span>
				<span role="cell"><PickupIdPill {person} /></span>
			{/snippet}
		</GridTable>
	</section>
</div>
