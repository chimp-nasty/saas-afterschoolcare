<!--
    Admin › Staff: everyone who works at the location. Admins and
    superadmins add staff (invited by email), resend invites, correct names
    and reset staff PINs; superadmins also make or unmake admins and remove
    people (the API decides by permission; buttons follow it). Superadmins
    are listed but managed with the business's setup, not here.
-->
<script lang="ts">
    import { invalidate } from "$app/navigation";
    import { toast } from "svelte-sonner";

    import Button from "$lib/components/actions/Button.svelte";
    import GridTable from "$lib/components/layout/GridTable.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import Modal from "$lib/components/overlays/Modal.svelte";
    import { confirmAction } from "$lib/components/overlays/confirm.svelte";
    import AddStaffForm from "$lib/features/staff/components/AddStaffForm.svelte";
    import RenameStaffForm from "$lib/features/staff/components/RenameStaffForm.svelte";

    import { auth } from "$lib/auth/state.svelte";
    import { createStaffAccountsApi } from "$lib/api/auth/adapters/staffAccounts";
    import type { AddStaffRequest, RenameStaffRequest, StaffAccountResponse } from "$lib/api/schema";
    import { formatTimestamp } from "$lib/utils/helpers";

    let { data } = $props();

    const staffApi = createStaffAccountsApi();

    // Superadmins make or unmake admins and remove people.
    const isSuperadmin = $derived($auth.roles.includes("superadmin"));

    const ROLE_LABELS: Record<string, string> = { staff: "Staff", admin: "Admin", superadmin: "Superadmin" };

    let modal: Modal;
    let mode = $state<"add" | "edit" | null>(null);
    let editingId = $state<string | null>(null);
    const editing = $derived(data.staff.find((s) => s.user_id === editingId) ?? null);

    function open(next: "add" | "edit", staff: StaffAccountResponse | null = null) {
        mode = next;
        editingId = staff?.user_id ?? null;
        modal.open();
    }

    async function refresh() {
        await invalidate("app:staff-accounts");
    }

    async function add(body: AddStaffRequest) {
        const response = await staffApi.add(body);

        if (response.ok && response.data) {
            if (!response.data.invited) {
                toast.info(`${body.first_name} already has an account, so they log in as they already do.`);
            }
            modal.close();
            await refresh();
        }

        return response;
    }

    async function rename(body: RenameStaffRequest) {
        const response = await staffApi.rename(editingId!, body);

        if (response.ok) await refresh();

        return response;
    }

    async function resendInvite(staff: StaffAccountResponse) {
        await confirmAction({
            title: `Send ${staff.first_name} a new invite?`,
            message: `A new link goes to ${staff.email}. The one sent before stops working.`,
            confirmLabel: "Send invite",
            action: async () => {
                if ((await staffApi.resendInvite(staff.user_id)).ok) await refresh();
            }
        });
    }

    async function resetPin(staff: StaffAccountResponse) {
        await confirmAction({
            title: `Reset ${staff.first_name}'s staff PIN?`,
            message: `Their PIN stops working at the staff kiosk straight away. They set a new one on their account page.`,
            confirmLabel: "Reset PIN",
            tone: "danger",
            action: async () => {
                if ((await staffApi.resetPin(staff.user_id)).ok) await refresh();
            }
        });
    }

    async function changeRole(staff: StaffAccountResponse) {
        const role = staff.role_code === "admin" ? "staff" : "admin";

        await confirmAction({
            title: role === "admin" ? `Make ${staff.first_name} an admin?` : `Make ${staff.first_name} staff instead of an admin?`,
            message:
                role === "admin"
                    ? "Admins run the centre on the website: the run sheet, medical reviews, kiosks and staff."
                    : "They keep their staff kiosk access, and lose admin access on the website.",
            confirmLabel: role === "admin" ? "Make admin" : "Make staff",
            action: async () => {
                if ((await staffApi.changeRole(staff.user_id, { role })).ok) await refresh();
            }
        });
    }

    async function remove(staff: StaffAccountResponse) {
        await confirmAction({
            title: `Remove ${staff.first_name} ${staff.last_name} from this centre?`,
            message:
                "They can't log in here or use the staff kiosk, and any open shift is closed now. Their account and past records stay.",
            confirmLabel: "Remove",
            tone: "danger",
            action: async () => {
                if ((await staffApi.remove(staff.user_id)).ok) {
                    modal.close();
                    await refresh();
                }
            }
        });
    }

    const columns = "minmax(10rem,1.4fr) minmax(12rem,1.6fr) 7rem 5rem minmax(9rem,1fr) 6rem";
</script>

<Page width="wide">
    <PageHeader title="Staff" description="Everyone who works at this centre. New staff are emailed an invite to set their password.">
        {#snippet actions()}
            <Button onclick={() => open("add")}>Add staff</Button>
        {/snippet}
    </PageHeader>

    <GridTable
        items={data.staff}
        key={(staff) => staff.user_id}
        {columns}
        headers={["Name", "Email", "Role", "PIN set", "Last login", ""]}
        label="Staff"
        minWidth="52rem"
        empty="No staff yet."
    >
        {#snippet row(staff)}
            <span class="text-base font-semibold text-(--text)" role="cell">{staff.first_name} {staff.last_name}</span>
            <span class="text-base text-(--text-muted)" role="cell">{staff.email}</span>
            <span class="text-base text-(--text)" role="cell">{ROLE_LABELS[staff.role_code] ?? staff.role_code}</span>
            <span class="text-base text-(--text)" role="cell">{staff.has_pin ? "Yes" : "No"}</span>
            <span class="text-base text-(--text-muted)" role="cell">
                {staff.last_login ? formatTimestamp(staff.last_login) : "Invited"}
            </span>
            <span role="cell">
                {#if staff.role_code !== "superadmin" && staff.user_id !== $auth.userId}
                    <Button variant="ghost" fullWidth onclick={() => open("edit", staff)}>Edit</Button>
                {/if}
            </span>
        {/snippet}
    </GridTable>
</Page>

<Modal
    bind:this={modal}
    title={mode === "add" ? "Add staff" : editing ? `${editing.first_name} ${editing.last_name}` : ""}
    onclose={() => { mode = null; editingId = null; }}
>
    {#if mode === "add"}
        <AddStaffForm canMakeAdmins={isSuperadmin} onsubmit={add} />
    {:else if mode === "edit" && editing}
        <div class="flex flex-col gap-5">
            <RenameStaffForm staff={editing} onsubmit={rename} />

            <div class="grid grid-cols-2 gap-3">
                {#if !editing.last_login}
                    <Button variant="ghost" fullWidth onclick={() => resendInvite(editing)}>Resend invite</Button>
                {/if}
                {#if editing.has_pin}
                    <Button variant="ghost" fullWidth onclick={() => resetPin(editing)}>Reset staff PIN</Button>
                {/if}
                {#if isSuperadmin}
                    <Button variant="ghost" fullWidth onclick={() => changeRole(editing)}>
                        {editing.role_code === "admin" ? "Make staff" : "Make admin"}
                    </Button>
                    <Button variant="ghost" fullWidth onclick={() => remove(editing)}>Remove from centre</Button>
                {/if}
            </div>
        </div>
    {/if}
</Modal>
