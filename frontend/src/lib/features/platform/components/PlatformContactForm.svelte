<!--
    The platform's contact form (docs/platform-site.md): name, email, phone
    and business (optional), what it's about (using the software for your
    own business, or having software like this built) and the message. One
    field is hidden from people: only bots fill it in.
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import Select from '$lib/components/forms/fields/Select.svelte';

	import type { SubmitPlatformEnquiryRequest } from '$lib/api/schema';
	import { PLATFORM_ENQUIRY_TOPICS, type PlatformEnquiryTopic } from '$lib/features/platform/enquiries';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type Body = {
		name: string;
		email: string;
		phone: string;
		business_name: string;
		topic: PlatformEnquiryTopic | '';
		message: string;
		website: string;
	};

	let {
		topic = $bindable(''),
		onsubmit
	}: {
		// Chosen already from a link (?topic=), and read by the page.
		topic?: PlatformEnquiryTopic | '';
		onsubmit: SubmitHandler<SubmitPlatformEnquiryRequest>;
	} = $props();

	const TOPICS = Object.entries(PLATFORM_ENQUIRY_TOPICS).map(([value, label]) => ({ value, label }));

	function empty(): Body {
		return { name: '', email: '', phone: '', business_name: '', topic, message: '', website: '' };
	}

	let body = $state<Body>(empty());
	let errors = $state<FormErrors<Body>>({});
	let isLoading = $state(false);

	// The page shows the jnb-digital note for "having software built".
	$effect(() => {
		topic = body.topic;
	});

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({
				name: body.name,
				email: body.email,
				phone: body.phone || null,
				business_name: body.business_name || null,
				topic: body.topic as PlatformEnquiryTopic,
				message: body.message,
				website: body.website || null
			});

			errors = response.fieldErrors;

			if (response.ok) body = { ...empty(), topic: body.topic };
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Send message">
	<Field label="What's it about?" error={errors.topic}>
		{#snippet children(id)}
			<Select {id} bind:value={body.topic} required placeholder="Choose one" options={TOPICS} />
		{/snippet}
	</Field>

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

		<Field label="Business (optional)" error={errors.business_name}>
			{#snippet children(id)}
				<input {id} type="text" autocomplete="organization" maxlength="200" bind:value={body.business_name} />
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
