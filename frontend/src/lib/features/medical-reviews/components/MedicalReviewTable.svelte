<!--
    Children in the staff review list; each row opens the child's review.
-->
<script lang="ts">
	import DataTable, { type DataTableColumn } from '$lib/components/layout/DataTable.svelte';

	import type { MedicalReviewSummaryResponse } from '$lib/api/schema';
	import { formatDateDDMMYYYY, formatPhone, formatTimestampDDMMYYYY } from '$lib/utils/helpers';

	let {
		reviews,
		locationCode,
		empty
	}: {
		reviews: MedicalReviewSummaryResponse[];
		locationCode: string;
		empty: string;
	} = $props();

	const columns: DataTableColumn<MedicalReviewSummaryResponse>[] = [
		{ label: 'Child', value: (review) => `${review.first_name} ${review.last_name}` },
		{ label: 'Date of birth', value: (review) => formatDateDDMMYYYY(review.dob) },
		{ label: 'Family', value: (review) => `${review.family_first_name} ${review.family_last_name}` },
		{ label: 'Phone', value: (review) => (review.family_phone ? formatPhone(review.family_phone) : null) },
		{ label: 'Documents', value: (review) => review.document_count },
		{ label: 'Since', value: (review) => formatTimestampDDMMYYYY(review.status_since) }
	];
</script>

<DataTable
	rows={reviews}
	{columns}
	rowKey={(review) => review.child_id}
	rowHref={(review) => `/${locationCode}/staff/reviews/${review.child_id}`}
	{empty}
/>
