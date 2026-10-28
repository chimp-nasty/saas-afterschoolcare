<!--
    The centre page's contact form (docs/enquiries.md): name, email, phone
    (optional), what it's about and the message. A logged-in family's name
    and email are filled in. One field is hidden from people: only bots
    fill it in, and the server quietly drops those.
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import Select from '$lib/components/forms/fields/Select.svelte';

	import type { SubmitEnquiryRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';
	import { ENQUIRY_TOPICS, ENQUIRY_TOPIC_LABELS, type EnquiryTopic } from '../enquiries';

	type EnquiryFormBody = {
		name: string;
		email: string;
		phone: string;
		topic: EnquiryTopic | '';
		message: string;
		website: string;
	};

	let {
		name = '',
		email = '',
		onsubmit
	}: {
		// Filled in for a logged-in family.
		name?: string;
		email?: string;
		onsubmit: SubmitHandler<SubmitEnquiryRequest>;
	} = $props();

	function empty(): EnquiryFormBody {
		return { name, email, phone: '', topic: '', message: '', website: '' };
	}

	let body = $state<EnquiryFormBody>(empty());
	let errors = $state<FormErrors<EnquiryFormBody>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({
				name: body.name,
				email: body.email,
				phone: body.phone || null,
				topic: body.topic as EnquiryTopic,
				message: body.message,
				website: body.website || null
			});

			errors = response.fieldErrors;

			if (response.ok) {
				body = empty();
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Send message">
	<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
		<Field label="Your name" error={errors.name}>
			{#snippet children(id)}
				<input {id} type="text" autocomplete="name" maxlength="200" bind:value={body.name} required />
			{/snippet}
		</Field>

		<Field label="Email" error={errors.email}>
			{#snippet children(id)}
				<input {id} type="email" autocomplete="email" inputmode="email" maxlength="255" bind:value={body.email} required />
			{/snippet}
		</Field>

		<Field label="Phone (optional)" error={errors.phone}>
			{#snippet children(id)}
				<input {id} type="tel" autocomplete="tel" inputmode="tel" maxlength="30" bind:value={body.phone} />
			{/snippet}
		</Field>

		<Field label="What's it about?" error={errors.topic}>
			{#snippet children(id)}
				<Select
					{id}
					bind:value={body.topic}
					required
					placeholder="Choose a topic"
					options={ENQUIRY_TOPICS.map((topic) => ({ value: topic, label: ENQUIRY_TOPIC_LABELS[topic] }))}
				/>
			{/snippet}
		</Field>
	</div>

	<Field label="Message" error={errors.message}>
		{#snippet children(id)}
			<textarea {id} rows="5" maxlength="3000" bind:value={body.message} required></textarea>
		{/snippet}
	</Field>

	<!-- Hidden from people (and screen readers); bots fill it in. -->
	<div class="absolute -left-[10000px] h-px w-px overflow-hidden" aria-hidden="true">
		<label>
			Website
			<input type="text" tabindex="-1" autocomplete="off" bind:value={body.website} />
		</label>
	</div>
</Form>
