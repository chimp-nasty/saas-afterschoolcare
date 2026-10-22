<script lang="ts">
    import { invalidate } from "$app/navigation";
    import { page } from "$app/state";
    import { onDestroy } from "svelte";

    import ActionBar from "$lib/components/actions/ActionBar.svelte";
    import Button from "$lib/components/actions/Button.svelte";
    import CheckboxRow from "$lib/components/forms/CheckboxRow.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import Modal from "$lib/components/overlays/Modal.svelte";
    import { confirmAction } from "$lib/components/overlays/confirm.svelte";
    import SectionHeading from "$lib/components/text/SectionHeading.svelte";
    import KioskDeviceCard from "$lib/features/kiosk/components/KioskDeviceCard.svelte";
    import { KIOSK_KINDS, type KioskKind } from "$lib/features/kiosk/devices";

    import { createKioskDevicesApi } from "$lib/api/public/adapters/kioskDevices";
    import type { KioskDeviceResponse, KioskSetupCodeResponse } from "$lib/api/schema";

    let { data } = $props();

    const kioskDevicesApi = createKioskDevicesApi();

    const active = (kind: KioskKind) =>
        data.devices.find((device) => device.kind === kind && device.is_active) ?? null;

    const kioskUrl = $derived(`${page.url.origin}/${data.locationCode}/kiosk`);

    let busy = $state(false);
    let codeModal: Modal;
    let setup = $state<KioskSetupCodeResponse | null>(null);
    let secondsLeft = $state(0);
    let ticker: ReturnType<typeof setInterval> | null = null;

    // The code is shown once; it's only good for 15 minutes.
    function showCode(result: KioskSetupCodeResponse) {
        setup = result;

        const tick = () => {
            secondsLeft = Math.max(0, Math.round((new Date(result.expires_at).getTime() - Date.now()) / 1000));
        };

        tick();
        if (ticker) clearInterval(ticker);
        ticker = setInterval(tick, 1000);
        codeModal.open();
    }

    function closeCode() {
        if (ticker) clearInterval(ticker);
        ticker = null;
        setup = null;
    }

    async function add(kind: KioskKind) {
        busy = true;

        try {
            const response = await kioskDevicesApi.create({ kind, name: KIOSK_KINDS[kind].defaultName });

            if (response.ok && response.data) {
                await invalidate("app:kiosk-devices");
                showCode(response.data);
            }
        } finally {
            busy = false;
        }
    }

    async function newCode(device: KioskDeviceResponse) {
        const confirmed = await confirmAction({
            title: `New setup code for the ${KIOSK_KINDS[device.kind].label.toLowerCase()}?`,
            message: "The tablet it's paired with now stops working until it's set up again with the new code.",
            confirmLabel: "New setup code",
        });

        if (!confirmed) return;

        const response = await kioskDevicesApi.newSetupCode(device.id);

        if (response.ok && response.data) {
            await invalidate("app:kiosk-devices");
            showCode(response.data);
        }
    }

    async function revoke(device: KioskDeviceResponse) {
        await confirmAction({
            title: `Revoke the ${KIOSK_KINDS[device.kind].label.toLowerCase()}?`,
            message: "Its tablet stops working straight away. Do this if a tablet is lost or stolen. You can add a new one afterwards.",
            confirmLabel: "Revoke",
            tone: "danger",
            action: async () => {
                const response = await kioskDevicesApi.revoke(device.id);

                if (response.ok) {
                    await invalidate("app:kiosk-devices");
                }
            },
        });
    }

    let savingSettings = $state(false);

    // Saves as soon as it's ticked or unticked.
    async function setServiceTimes(enabled: boolean) {
        savingSettings = true;

        try {
            await kioskDevicesApi.updateSettings({ enforce_service_times: enabled });
        } finally {
            // Shows what was saved (or puts the box back if it failed).
            await invalidate("app:kiosk-devices");
            savingSettings = false;
        }
    }

    onDestroy(() => closeCode());
</script>

<Page width="wide">
    <PageHeader
        title="Kiosks"
        description="Your centre's two tablets: one for families at the entrance, one for staff. Each is set up once with a code from here."
    />

    <div class="grid grid-cols-1 gap-6 md:grid-cols-2">
        {#each ["family", "staff"] as const as kind (kind)}
            <KioskDeviceCard
                {kind}
                device={active(kind)}
                {busy}
                onadd={() => add(kind)}
                onnewcode={newCode}
                onrevoke={revoke}
            />
        {/each}
    </div>

    {#if data.settings}
        <section class="flex flex-col gap-3">
            <SectionHeading title="Kiosk rules" />

            <Card border>
                <CheckboxRow
                    checked={data.settings.enforce_service_times}
                    title="Enforce service times"
                    help="Applies at both kiosks. Outside those times, children can't be signed in or out on the kiosks; staff deal with it in person."
                    disabled={savingSettings}
                    onchange={setServiceTimes}
                />
            </Card>
        </section>
    {/if}
</Page>

<Modal
    bind:this={codeModal}
    title="Set up the tablet"
    description={`On the tablet, open ${kioskUrl} and type this code:`}
    onclose={closeCode}
>
    {#if setup}
        <div class="flex flex-col gap-4">
            <p class="text-center text-4xl font-extrabold tracking-[0.3em] text-(--text)">{setup.setup_code}</p>

            <p class="text-center text-sm text-(--text-muted)">
                {#if secondsLeft > 0}
                    Valid for {Math.floor(secondsLeft / 60)}:{String(secondsLeft % 60).padStart(2, "0")}. It works once, and won't be shown again.
                {:else}
                    This code has expired. Choose New setup code to get another.
                {/if}
            </p>
        </div>
    {/if}

    {#snippet actions()}
        <ActionBar>
            <Button onclick={() => codeModal.close()}>Done</Button>
        </ActionBar>
    {/snippet}
</Modal>
