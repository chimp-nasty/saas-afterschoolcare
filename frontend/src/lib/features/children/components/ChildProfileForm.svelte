<script lang="ts">
    import Form from "$lib/components/forms/Form.svelte";
    import Field from "$lib/components/forms/Field.svelte";

    import type { CreateChildRequest } from "$lib/api/schema";
    import type { FormErrors, SubmitHandler } from '$lib/types/forms';

    let {
		askPickupConsent = false,
		onsubmit
	}: {
		// The family has pickup people besides the account holder, who'll
		// be able to collect this child too.
		askPickupConsent?: boolean;
		onsubmit: SubmitHandler<CreateChildRequest>;
	} = $props();

    const initialBody: CreateChildRequest = {
		first_name: '',
		last_name: '',
        dob: '',
        medical_info: '',
        allergy_info: '',
        medication_info: '',
        pickup_consent: false
	};

	let body = $state<CreateChildRequest>({ ...initialBody });
    let errors = $state<FormErrors<CreateChildRequest>>({});
    let isLoading = $state(false);

    async function submit() {
        errors = {};
        isLoading = true;

        try {
            const response = await onsubmit(body);

            errors = response.fieldErrors;

            if (response.ok) {
                body = { ...initialBody };
            }
        } finally {
            isLoading = false;
        }
    }
</script>

<Form
    {isLoading}
    handleSubmit={submit}
    submitLabel="Add child"
>
    <Field label="First name" error={errors.first_name}>
        {#snippet children(id)}
            <input {id} type="text" autocomplete="off" bind:value={body.first_name} required />
        {/snippet}
    </Field>

    <Field label="Last name" error={errors.last_name}>
        {#snippet children(id)}
            <input {id} type="text" autocomplete="off" bind:value={body.last_name} required />
        {/snippet}
    </Field>

    <Field label="Date of birth" error={errors.dob}>
        {#snippet children(id)}
            <input {id} type="date" bind:value={body.dob} required />
        {/snippet}
    </Field>

    <Field label="Medical conditions" error={errors.medical_info}>
        {#snippet children(id)}
            <textarea {id} rows="4" bind:value={body.medical_info}></textarea>
        {/snippet}
    </Field>

    <Field label="Allergies" error={errors.allergy_info}>
        {#snippet children(id)}
            <textarea {id} rows="4" bind:value={body.allergy_info}></textarea>
        {/snippet}
    </Field>

    <Field label="Medication" error={errors.medication_info}>
        {#snippet children(id)}
            <textarea {id} rows="4" bind:value={body.medication_info}></textarea>
        {/snippet}
    </Field>
    {#if askPickupConsent}
        <Field
            label={`Everyone on my pickup list may collect ${body.first_name.trim() || "this child"}`}
            error={errors.pickup_consent}
            inline
        >
            {#snippet children(id)}
                <input {id} type="checkbox" bind:checked={body.pickup_consent} required />
            {/snippet}
        </Field>
    {/if}
</Form>