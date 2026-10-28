<!--
    /{location}/settings (Settings in the menu): changing your password, and
    deactivating your account here (docs/account-deactivation.md).
    Deactivating needs your password, no upcoming bookings (the server says
    so if there are) and a confirmation; then the layout shows only the
    deactivated page.
-->
<script lang="ts">
    import { invalidate } from "$app/navigation";

    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import SectionHeading from "$lib/components/text/SectionHeading.svelte";
    import ChangePasswordForm from "$lib/features/account/components/ChangePasswordForm.svelte";
    import DeactivateAccountForm from "$lib/features/account/components/DeactivateAccountForm.svelte";
    import { confirmAction } from "$lib/components/overlays/confirm.svelte";

    import { createAccountApi } from "$lib/api/auth/adapters/account";
    import type { ApiResponse } from "$lib/api/wrapper";
    import type { ChangePasswordRequest, DeactivateAccountRequest } from "$lib/api/schema";

    let { data } = $props();

    const accountApi = createAccountApi();

    const centre = $derived(data.location.location_name);

    function changePassword(body: ChangePasswordRequest) {
        return accountApi.changePassword(body);
    }

    async function deactivate(body: DeactivateAccountRequest): Promise<ApiResponse<null>> {
        let response: ApiResponse<null> = { ok: false, msg: "", data: null, status: 0, fieldErrors: {} };

        await confirmAction({
            title: "Deactivate your account?",
            message: `You won't be able to book or manage anything at ${centre} until they reactivate your account. You can ask them to from the next page.`,
            confirmLabel: "Deactivate account",
            tone: "danger",
            action: async () => {
                response = await accountApi.deactivate(body);

                // The layout now shows only the deactivated page.
                if (response.ok) {
                    await invalidate("app:session");
                }
            },
        });

        return response;
    }
</script>

<Page>
    <PageHeader title="Account settings" />

    <section class="flex flex-col gap-3">
        <SectionHeading title="Change password" />

        <ChangePasswordForm onsubmit={changePassword} />
    </section>

    <section class="flex flex-col gap-3">
        <SectionHeading
            title="Deactivate your account"
            description={`Stop using your account at ${centre}. Cancel or refund any upcoming bookings first. Your details stay with ${centre} for as long as the law requires childcare records to be kept. To come back, ask them to reactivate it.`}
        />

        <DeactivateAccountForm onsubmit={deactivate} />
    </section>
</Page>
