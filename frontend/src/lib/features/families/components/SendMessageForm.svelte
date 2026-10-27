<!--
    A message to the family, read in their account. The admin writes the
    title and the middle of the message: "Dear {first name}," and the
    centre's sign-off are added around it, shown here read-only. Optionally
    about one child, and optionally linking to a page in their account: an
    account page, or with a child, one of that child's pages. Choosing a
    link fills in a blank title to match (it can be changed). The family is
    emailed only that there's a message; its text stays in the app. A short
    guide says what messages are for, since much is already sent
    automatically.
-->
<script lang="ts">
	import ExpandableSection from '$lib/components/controls/ExpandableSection.svelte';
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import Select from '$lib/components/forms/fields/Select.svelte';

	import type { FamilyChildResponse, SendFamilyMessageRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';
	import { composeMessage, messageBodyMaxLength, type MessageFrame } from '../message';

	type Link = NonNullable<SendFamilyMessageRequest['target']>;

	let {
		kids,
		frame,
		onsubmit
	}: {
		// The family's current children.
		kids: FamilyChildResponse[];
		// The greeting and sign-off around what the admin writes.
		frame: MessageFrame;
		onsubmit: SubmitHandler<SendFamilyMessageRequest>;
	} = $props();

	// The pages a message can link to (the backend's ACCOUNT_LINKS and CHILD_LINKS).
	const ACCOUNT_LINKS: { value: Link; label: string }[] = [
		{ value: 'profile', label: 'Their details' },
		{ value: 'children', label: 'Their children' },
		{ value: 'pickups', label: 'Their pickup people' }
	];
	const CHILD_LINKS: { value: Link; label: string }[] = [
		{ value: 'profile', label: "The child's details" },
		{ value: 'manage-documents', label: "The child's documents" }
	];

	// A title to match a link, used when the title is still blank.
	function titleFor(link: Link, childName: string | null): string {
		if (childName) {
			return link === 'manage-documents' ? `Documents for ${childName}` : `Please check ${childName}'s details`;
		}

		return {
			profile: 'Please check your details',
			children: "Please check your children's details",
			pickups: 'Please check your pickup people',
			'manage-documents': 'Documents needed'
		}[link];
	}

	let title = $state('');
	let body = $state('');
	let childId = $state('');
	let target = $state<Link | ''>('');
	let errors = $state<FormErrors<SendFamilyMessageRequest>>({});
	let isLoading = $state(false);

	const links = $derived(childId ? CHILD_LINKS : ACCOUNT_LINKS);
	const maxLength = $derived(messageBodyMaxLength(frame));

	// A link chosen for the whole family may not exist for a child.
	function chooseChild(value: string) {
		childId = value;

		if (target && !links.some((link) => link.value === target)) {
			target = '';
		}
	}

	function chooseLink(value: Link | '') {
		target = value;

		if (value && !title.trim()) {
			title = titleFor(value, kids.find((child) => child.id === childId)?.first_name ?? null);
		}
	}

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({
				title,
				message: composeMessage(frame, body),
				child_id: childId || null,
				target: target || null
			});

			errors = response.fieldErrors;

			if (response.ok) {
				title = '';
				body = '';
				childId = '';
				target = '';
			}
		} finally {
			isLoading = false;
		}
	}
</script>

{#snippet fixedText(text: string)}
	<p class="rounded-lg bg-(--surface-muted) px-3 py-2 text-base whitespace-pre-line text-(--text-muted)">{text}</p>
{/snippet}

<Form {isLoading} handleSubmit={submit} submitLabel="Send message">
	<ExpandableSection title="What messages are for">
		<div class="flex flex-col gap-3 text-sm text-(--text)">
			<div>
				<p class="font-semibold">Something only this family needs to know or do, e.g.</p>
				<ul class="list-disc pl-5">
					<li>a request: update their pickup people, collect lost property</li>
					<li>a change that affects them, like new session times</li>
					<li>following up a late pickup or an unpaid booking</li>
				</ul>
			</div>
			<div>
				<p class="font-semibold">Already sent automatically, so no message is needed</p>
				<ul class="list-disc pl-5">
					<li>booking and refund confirmations</li>
					<li>medical reviews: asking for documents, and clearing a child for bookings</li>
					<li>kiosk PINs, password and account emails</li>
				</ul>
			</div>
			<div>
				<p class="font-semibold">Not for</p>
				<ul class="list-disc pl-5">
					<li>anything urgent: phone the family</li>
					<li>health details: ask for documents through the child's medical review</li>
					<li>child protection concerns: follow the centre's procedure</li>
				</ul>
			</div>
		</div>
	</ExpandableSection>

	<Field label="Title" error={errors.title}>
		{#snippet children(id)}
			<input {id} type="text" maxlength="120" bind:value={title} required />
		{/snippet}
	</Field>

	<Field label="Message" error={errors.message}>
		{#snippet children(id)}
			<div class="flex flex-col gap-2">
				{@render fixedText(frame.greeting)}
				<textarea {id} rows="6" maxlength={maxLength} bind:value={body} required></textarea>
				{@render fixedText(frame.signOff)}
			</div>
		{/snippet}
	</Field>

	<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
		<Field label="About" error={errors.child_id}>
			{#snippet children(id)}
				<Select
					{id}
					value={childId}
					onchange={chooseChild}
					options={[
						{ value: '', label: 'The whole family' },
						...kids.map((child) => ({ value: child.id, label: `${child.first_name} ${child.last_name}` }))
					]}
				/>
			{/snippet}
		</Field>

		<Field label="Link to" error={errors.target}>
			{#snippet children(id)}
				<Select
					{id}
					value={target}
					onchange={(value) => chooseLink(value as Link | '')}
					options={[{ value: '', label: 'No link' }, ...links]}
				/>
			{/snippet}
		</Field>
	</div>

	<p class="text-sm text-(--text-muted)">The family is emailed that there's a new message. The email doesn't include what it says.</p>
</Form>
