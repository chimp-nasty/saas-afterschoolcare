<!--
    /{location}/setup: setting up a new family's account, one step per
    screen (?step=), straight after registering (opening with a welcome,
    WelcomeModal) and from the home page's "Finish setting up" card. Each step saves as it goes, through the same
    forms and API as Account, so leaving halfway keeps what's done.

    1. Your details (phone, address)   2. Emergency contact
    3. Your children                   4. Who can collect (optional)
    then what to do next.

    Booking needs the first three (missingForBooking); nothing here is
    forced, and booking still checks.
-->
<script lang="ts">
    import { page } from "$app/state";
    import { goto, invalidate } from "$app/navigation";

    import ActionBar from "$lib/components/actions/ActionBar.svelte";
    import Button from "$lib/components/actions/Button.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import Notice from "$lib/components/text/Notice.svelte";
    import SectionHeading from "$lib/components/text/SectionHeading.svelte";
    import ParentProfileForm from "$lib/features/customer/components/ParentProfileForm.svelte";
    import EmergencyContactForm from "$lib/features/customer/components/EmergencyContactForm.svelte";
    import ChildProfileForm from "$lib/features/children/components/ChildProfileForm.svelte";
    import PickupForm, { type PickupFormValues } from "$lib/features/pickups/components/PickupForm.svelte";
    import WelcomeModal from "$lib/features/customer/components/WelcomeModal.svelte";

    import { createCustomerApi } from "$lib/api/public/adapters/customer";
    import { createChildrenApi } from "$lib/api/public/adapters/children";
    import { createPickupsApi } from "$lib/api/public/adapters/pickups";
    import type { CreateChildRequest, UpdateCustomerProfileRequest } from "$lib/api/schema";
    import { REVIEW_STATUS_LABELS } from "$lib/features/children/review";
    import {
        SETUP_STEPS,
        SETUP_STEP_TITLES,
        setupHref,
        setupProgress,
        type SetupStep,
    } from "$lib/features/customer/setup";

    let { data } = $props();

    const customerApi = createCustomerApi();
    const childrenApi = createChildrenApi();
    const pickupsApi = createPickupsApi();

    const progress = $derived(setupProgress(data.profile, data.children.length));

    // ?step=, else the first step still to do (the last screen once the
    // required ones are done).
    const step = $derived.by((): SetupStep => {
        const asked = page.url.searchParams.get("step");

        if (asked === "done" || SETUP_STEPS.includes(asked as (typeof SETUP_STEPS)[number])) {
            return asked as SetupStep;
        }

        return progress.next ?? "done";
    });

    const stepNumber = $derived(step === "done" ? null : SETUP_STEPS.indexOf(step) + 1);

    const otherPickups = $derived(data.pickups.filter((pickup) => !pickup.is_account_holder));

    // Adding another child while some are listed.
    let addingChild = $state(false);
    let addingPickup = $state(false);

    function go(next: SetupStep) {
        addingChild = false;
        addingPickup = false;

        void goto(setupHref(data.locationCode, next));
    }

    function previous(current: (typeof SETUP_STEPS)[number]): () => void {
        const index = SETUP_STEPS.indexOf(current);

        return () => go(SETUP_STEPS[index - 1]);
    }

    async function saveProfile(body: UpdateCustomerProfileRequest, next: SetupStep) {
        const response = await customerApi.updateProfile(body);

        if (response.ok) {
            await invalidate("app:customer-account");
            go(next);
        }

        return response;
    }

    async function addChild(body: CreateChildRequest) {
        const response = await childrenApi.create(body);

        if (response.ok) {
            addingChild = false;
            await invalidate("app:customer-account");
        }

        return response;
    }

    // The declaration boxes are required in the form, so they're ticked.
    async function addPickup(values: PickupFormValues) {
        const response = await pickupsApi.create({
            ...values,
            consent_confirmed: true,
            adult_confirmed: true,
        });

        if (response.ok) {
            addingPickup = false;
            await invalidate("app:customer-account");
        }

        return response;
    }
</script>

<!-- Straight after registering only. -->
<WelcomeModal businessName={data.location.tenant_name} />

<Page>
    {#if step === "done"}
        <PageHeader
            title={progress.next ? "Nearly there" : "You're ready to book"}
            description={progress.next
                ? "A few things are still needed before you can book. You can finish them any time."
                : "Your account is set up. Here's what to do next."}
        />

        {#if progress.next}
            <Notice tone="warning">
                Still to do: {[
                    !progress.details && "your details",
                    !progress.emergency && "an emergency contact",
                    !progress.children && "a child",
                ].filter(Boolean).join(", ")}.
            </Notice>
        {/if}

        <Card border>
            <div class="flex flex-col gap-4">
                <SectionHeading title="Next steps" />

                <ol class="flex list-decimal flex-col gap-3 pl-5 text-base text-(--text)">
                    <li>Book sessions for your children from <span class="font-semibold">Book now</span>.</li>
                    <li>If a child has a medical condition, upload their action plan from Account › Children. Staff review it before they can be booked.</li>
                    <li>Check <span class="font-semibold">Messages</span> (the bell) for anything the centre sends you.</li>
                    <li>Add or change pickup people any time from Account › Pickups.</li>
                </ol>
            </div>
        </Card>

        <ActionBar>
            {#if progress.next}
                <Button variant="ghost" onclick={() => go(progress.next ?? "details")}>Finish setting up</Button>
            {:else}
                <Button variant="ghost" onclick={() => goto(`/${data.locationCode}/home`)}>Go to home</Button>
            {/if}

            <Button
                isDisabled={!!progress.next}
                onclick={() => goto(`/${data.locationCode}/bookings/new`)}
            >
                Book now
            </Button>
        </ActionBar>
    {:else}
        <PageHeader
            eyebrow={`Step ${stepNumber} of ${SETUP_STEPS.length}`}
            title={SETUP_STEP_TITLES[step]}
            description={{
                details: "Your phone number and address, so the centre can reach you.",
                emergency: "Someone the centre can call if they can't reach you.",
                children: "Children with medical conditions, allergies or medication are reviewed by staff before they can be booked.",
                pickups: "Anyone besides you who may collect your children. You can skip this and add them later.",
            }[step]}
        />

        {#if step === "details"}
            <ParentProfileForm
                profile={data.profile}
                submitLabel="Continue"
                onsubmit={(body) => saveProfile(body, "emergency")}
            />
        {:else if step === "emergency"}
            <EmergencyContactForm
                profile={data.profile}
                submitLabel="Continue"
                oncancel={previous("emergency")}
                cancelLabel="Back"
                onsubmit={(body) => saveProfile(body, "children")}
            />
        {:else if step === "children"}
            {#if data.children.length > 0}
                <Card border>
                    <div class="flex flex-col gap-4">
                        <SectionHeading title="Added" />

                        <ul class="flex flex-col divide-y divide-(--border)">
                            {#each data.children as child (child.id)}
                                <li class="flex items-center justify-between gap-4 py-3">
                                    <span class="text-base font-semibold text-(--text)">{child.first_name} {child.last_name}</span>
                                    <span class="text-sm text-(--text-muted)">{REVIEW_STATUS_LABELS[child.review_status]}</span>
                                </li>
                            {/each}
                        </ul>
                    </div>
                </Card>
            {/if}

            {#if data.children.length === 0 || addingChild}
                <ChildProfileForm
                    askPickupConsent={otherPickups.length > 0}
                    oncancel={data.children.length === 0 ? previous("children") : () => (addingChild = false)}
                    cancelLabel={data.children.length === 0 ? "Back" : "Cancel"}
                    onsubmit={addChild}
                />
            {:else}
                <ActionBar start>
                    <Button variant="ghost" onclick={() => (addingChild = true)}>Add another child</Button>
                </ActionBar>

                <ActionBar>
                    <Button variant="ghost" onclick={previous("children")}>Back</Button>
                    <Button onclick={() => go("pickups")}>Continue</Button>
                </ActionBar>
            {/if}
        {:else if step === "pickups"}
            {#if otherPickups.length > 0}
                <Card border>
                    <div class="flex flex-col gap-4">
                        <SectionHeading title="Added" />

                        <ul class="flex flex-col divide-y divide-(--border)">
                            {#each otherPickups as pickup (pickup.id)}
                                <li class="py-3 text-base font-semibold text-(--text)">{pickup.first_name} {pickup.last_name}</li>
                            {/each}
                        </ul>
                    </div>
                </Card>
            {/if}

            {#if addingPickup}
                <PickupForm
                    submitLabel="Add pickup person"
                    oncancel={() => (addingPickup = false)}
                    onsubmit={addPickup}
                />

                <p class="text-sm text-(--text-muted)">
                    We'll email them a kiosk PIN, which they'll change the first time they sign in at the centre.
                    Staff check their photo ID before they can collect.
                </p>
            {:else}
                <ActionBar start>
                    <Button variant="ghost" onclick={() => (addingPickup = true)}>
                        {otherPickups.length > 0 ? "Add another pickup person" : "Add a pickup person"}
                    </Button>
                </ActionBar>

                <ActionBar>
                    <Button variant="ghost" onclick={previous("pickups")}>Back</Button>
                    <Button onclick={() => go("done")}>{otherPickups.length > 0 ? "Continue" : "Skip for now"}</Button>
                </ActionBar>
            {/if}
        {/if}
    {/if}
</Page>
