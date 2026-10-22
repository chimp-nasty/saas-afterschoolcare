<!--
    Children in the staff review list; each row opens the child's review.
    The approved list shows who approved each child and when instead of
    their documents.
-->
<script lang="ts">
	import DataTable, { type DataTableColumn } from '$lib/components/layout/DataTable.svelte';

	import type { MedicalReviewSummaryResponse } from '$lib/api/schema';
	import { formatDateDDMMYYYY, formatPhone, formatTimestampDDMMYYYY } from '$lib/utils/helpers';

	let {
		reviews,
		locationCode,
		empty,
		approved = false
	}: {
		reviews: MedicalReviewSummaryResponse[];
		locationCode: string;
		empty: string;
		// The approved list: who approved them, and when.
		approved?: boolean;
	} = $props();

	const waitingColumns: DataTableColumn<MedicalReviewSummaryResponse>[] = [
		{ label: 'Child', value: (review) => `${review.first_name} ${review.last_name}` },
		{ label: 'Date of birth', value: (review) => formatDateDDMMYYYY(review.dob) },
		{ label: 'Family', value: (review) => `${review.family_first_name} ${review.family_last_name}` },
		{ label: 'Phone', value: (review) => (review.family_phone ? formatPhone(review.family_phone) : null) },
		{ label: 'Documents', value: (review) => review.document_count },
		{ label: 'Since', value: (review) => formatTimestampDDMMYYYY(review.status_since) }
	];

	const approvedColumns: DataTableColumn<MedicalReviewSummaryResponse>[] = [
		...waitingColumns.slice(0, 4),
		{ label: 'Approved by', value: (review) => review.reviewed_by },
		{ label: 'Approved', value: (review) => formatTimestampDDMMYYYY(review.status_since) }
	];

	const columns = $derived(approved ? approvedColumns : waitingColumns);
</script>

<DataTable
	rows={reviews}
	{columns}
	rowKey={(review) => review.child_id}
	rowHref={(review) => `/${locationCode}/admin/reviews/${review.child_id}`}
	{empty}
/>
