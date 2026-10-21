<!--
    The staff portal: your own account, for everyone who works here (staff,
    admins, superadmins). Nothing about children or families: those are in
    the admin portal and at the staff kiosk (docs/portals.md).
-->
<script lang="ts">
    import { invalidate } from "$app/navigation";

    import Card from "$lib/components/layout/Card.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import ChangePasswordForm from "$lib/features/account/components/ChangePasswordForm.svelte";
    import StaffPinForm from "$lib/features/staff/components/StaffPinForm.svelte";

    import { createAccountApi } from "$lib/api/auth/adapters/account";
    import { createStaffPinApi } from "$lib/api/auth/adapters/staffPin";
    import type { ChangePasswordRequest, SetStaffPinRequest } from "$lib/api/schema";
    import { formatTimestamp } from "$lib/utils/helpers";

    let { data } = $props();

    const accountApi = createAccountApi();
    const staffPinApi = createStaffPinApi();

    async function savePin(body: SetStaffPinRequest) {
        const response = await staffPinApi.set(body);

        if (response.ok) {
            await invalidate("app:staff-pin");
        }

        return response;
    }

    function changePassword(body: ChangePasswordRequest) {
        return accountApi.changePassword(body);
    }
</script>

<Page>
    <PageHeader title="My account" />

    {#if data.account}
        <section class="flex flex-col gap-3">
            <h2 class="text-lg font-extrabold text-(--text)">Your details</h2>

            <Card border>
                <dl class="flex flex-col gap-3">
                    <div>
                        <dt class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">Name</dt>
                        <dd class="text-base text-(--text)">{data.account.first_name} {data.account.last_name}</dd>
                    </div>

                    <div>
                        <dt class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">Email</dt>
                        <dd class="text-base text-(--text) break-all">{data.account.email}</dd>
                    </div>

                    <div>
                        <dt class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">Where you work</dt>
                        <dd>
                            <ul class="flex flex-col gap-1">
                                {#each data.account.roles as role (`${role.location_code}:${role.role_code}`)}
                                    <li class="text-base text-(--text)">
                                        {role.location_name ?? role.location_code}: {role.role_name}
                                    </li>
                                {/each}
                            </ul>
                        </dd>
                    </div>
                </dl>

                <p class="mt-3 text-sm text-(--text-muted)">If something here is wrong, ask an admin to correct it.</p>
            </Card>
        </section>
    {/if}

    <section class="flex flex-col gap-3">
        <h2 class="text-lg font-extrabold text-(--text)">Staff PIN</h2>

        <Card border>
            {#if data.status?.is_locked}
                <p class="text-base font-semibold text-(--danger-text)">
                    Your PIN is locked after too many wrong tries at the kiosk. Set a new one below to unlock it.
                </p>
            {:else if data.status?.is_set && data.status.set_at}
                <p class="text-base text-(--text)">You set your PIN on {formatTimestamp(data.status.set_at)}.</p>
            {:else}
                <p class="text-base text-(--text)">You haven't set a PIN yet. You need one to use the staff kiosk.</p>
            {/if}

            <p class="mt-2 text-sm text-(--text-muted)">
                Your 4-digit PIN for the staff kiosk, where it records which staff member signed a child in or out, checked ID or started a shift. Never share it.
            </p>
        </Card>

        <StaffPinForm onsubmit={savePin} />
    </section>

    <section class="flex flex-col gap-3">
        <h2 class="text-lg font-extrabold text-(--text)">Change password</h2>

        <ChangePasswordForm onsubmit={changePassword} />
    </section>
</Page>
