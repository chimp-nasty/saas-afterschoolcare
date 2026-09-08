<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import EmailInput from '$lib/components/forms/fields/EmailInput.svelte';
	import PasswordInput from '$lib/components/forms/fields/PasswordInput.svelte';
    import TextInput from '$lib/components/forms/fields/TextInput.svelte';
    import CheckboxInput from '$lib/components/forms/fields/CheckboxInput.svelte';

	import type { FormErrors } from '$lib/types/forms';
	import { createFormState } from '$lib/utils/forms';

	let {
		handleSubmit,
		isLoading
	}: {
		handleSubmit: (body: Record<string, string>) => void | Promise<void>;
		isLoading: boolean;
	} = $props();
</script>
