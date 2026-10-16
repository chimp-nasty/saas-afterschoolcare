<script lang="ts">
    import Form from "$lib/components/forms/Form.svelte";
    import Field from "$lib/components/forms/Field.svelte";

    import type { CreateChildRequest } from "$lib/api/schema";
    import type { FormErrors, SubmitHandler } from '$lib/types/forms';

    let {
		onsubmit
	}: {
		onsubmit: SubmitHandler<CreateChildRequest>;
	} = $props();

    const initialBody: CreateChildRequest = {
		first_name: '',
		last_name: '',
        dob: '',
        medical_info: '',
        allergy_info: '',
        medication_info: ''
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
>
    <Field label="First Name" error={errors.first_name}>
        {#snippet children(id)}
            <input {id} type="text" bind:value={body.first_name} required />
        {/snippet}
    </Field>

    <Field label="Last Name" error={errors.last_name}>
        {#snippet children(id)}
            <input {id} type="text" bind:value={body.last_name} required />
        {/snippet}
    </Field>

    <Field label="Date of Birth" error={errors.dob}>
        {#snippet children(id)}
            <input {id} type="date" bind:value={body.dob} required />
        {/snippet}
    </Field>

    <Field label="Medical Info" error={errors.medical_info}>
        {#snippet children(id)}
            <textarea {id} rows="4" bind:value={body.medical_info}></textarea>
        {/snippet}
    </Field>

    <Field label="Allergy Info" error={errors.allergy_info}>
        {#snippet children(id)}
            <textarea {id} rows="4" bind:value={body.allergy_info}></textarea>
        {/snippet}
    </Field>

    <Field label="Medication Info" error={errors.medication_info}>
        {#snippet children(id)}
            <textarea {id} rows="4" bind:value={body.medication_info}></textarea>
        {/snippet}
    </Field>
</Form>