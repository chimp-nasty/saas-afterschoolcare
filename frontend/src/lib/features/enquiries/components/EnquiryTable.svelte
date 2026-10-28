<!--
    Enquiries in the admins' inbox, newest first; each row opens the
    enquiry.
-->
<script lang="ts">
	import DataTable, { type DataTableColumn } from '$lib/components/layout/DataTable.svelte';

	import type { EnquirySummaryResponse } from '$lib/api/schema';
	import { formatTimestampDDMMYYYY } from '$lib/utils/helpers';
	import { ENQUIRY_STATUS_LABELS, ENQUIRY_TOPIC_LABELS } from '../enquiries';

	let {
		enquiries,
		locationCode,
		empty
	}: {
		enquiries: EnquirySummaryResponse[];
		locationCode: string;
		empty: string;
	} = $props();

	const columns: DataTableColumn<EnquirySummaryResponse>[] = [
		{ label: 'Received', value: (enquiry) => formatTimestampDDMMYYYY(enquiry.created_at) },
		{ label: 'From', value: (enquiry) => enquiry.name },
		{ label: 'About', value: (enquiry) => ENQUIRY_TOPIC_LABELS[enquiry.topic] },
		{ label: 'Status', value: (enquiry) => ENQUIRY_STATUS_LABELS[enquiry.status] },
		{ label: 'Message', value: (enquiry) => enquiry.preview }
	];
</script>

<DataTable
	rows={enquiries}
	{columns}
	rowKey={(enquiry) => enquiry.id}
	rowHref={(enquiry) => `/${locationCode}/admin/enquiries/${enquiry.id}`}
	{empty}
/>
