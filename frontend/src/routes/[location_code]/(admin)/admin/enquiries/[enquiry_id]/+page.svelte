<!--
    Admin › Enquiries › one enquiry (docs/enquiries.md): what was sent, the
    replies so far, a reply (emailed to the person), and closing or
    reopening it.
-->
<script lang="ts">
    import { goto, invalidate } from "$app/navigation";

    import ActionBar from "$lib/components/actions/ActionBar.svelte";
    import Button from "$lib/components/actions/Button.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import LabelValueList from "$lib/components/text/LabelValueList.svelte";
    import Pill from "$lib/components/text/Pill.svelte";
    import SectionHeading from "$lib/components/text/SectionHeading.svelte";
    import EnquiryReplyForm from "$lib/features/enquiries/components/EnquiryReplyForm.svelte";

    import { createEnquiriesApi } from "$lib/api/public/adapters/enquiries";
    import type { EnquiryReplyRequest } from "$lib/api/schema";
    import { ENQUIRY_STATUS_LABELS, ENQUIRY_STATUS_TONES, ENQUIRY_TOPIC_LABELS } from "$lib/features/enquiries/enquiries";
    import { formatTimestamp } from "$lib/utils/helpers";

    let { data } = $props();

    const enquiriesApi = createEnquiriesApi();

    const enquiry = $derived(data.enquiry);
    const isClosed = $derived(enquiry.status === "closed");

    let busy = $state(false);

    async function reply(body: EnquiryReplyRequest) {
        const response = await enquiriesApi.reply(enquiry.id, body);

        if (response.ok) await invalidate("app:enquiry");

        return response;
    }

    async function setOpen(open: boolean) {
        busy = true;

        try {
            const response = open ? await enquiriesApi.reopen(enquiry.id) : await enquiriesApi.close(enquiry.id);

            if (response.ok) await invalidate("app:enquiry");
        } finally {
            busy = false;
        }
    }
</script>

<Page width="wide">
    <ActionBar start>
        <Button variant="ghost" onclick={() => goto(`/${data.locationCode}/admin/enquiries`)}>Back to enquiries</Button>
    </ActionBar>

    <PageHeader
        eyebrow={ENQUIRY_TOPIC_LABELS[enquiry.topic]}
        title={enquiry.name}
        description={`Received ${formatTimestamp(enquiry.created_at)}`}
    >
        {#snippet actions()}
            <div class="flex items-center gap-3">
                <Pill tone={ENQUIRY_STATUS_TONES[enquiry.status]}>{ENQUIRY_STATUS_LABELS[enquiry.status]}</Pill>

                <Button variant="ghost" width="w-32" isLoading={busy} isDisabled={busy} onclick={() => setOpen(isClosed)}>
                    {isClosed ? "Reopen" : "Close"}
                </Button>
            </div>
        {/snippet}
    </PageHeader>

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div class="flex flex-col gap-6">
            <Card border>
                <div class="flex flex-col gap-4">
                    <SectionHeading title="Their message" />
                    <p class="text-base whitespace-pre-line text-(--text)">{enquiry.message}</p>
                </div>
            </Card>

            {#each enquiry.replies as sent (sent.id)}
                <Card border>
                    <div class="flex flex-col gap-2">
                        <p class="label-text">
                            Reply{sent.staff_name ? ` from ${sent.staff_name}` : ""} · {formatTimestamp(sent.created_at)}
                        </p>
                        <p class="text-base whitespace-pre-line text-(--text)">{sent.body}</p>
                    </div>
                </Card>
            {/each}

            <section class="flex flex-col gap-3">
                <SectionHeading
                    title={enquiry.replies.length ? "Reply again" : "Reply"}
                    description="Sent by email as your centre. If they answer, it goes to your centre's contact email."
                />

                <EnquiryReplyForm onsubmit={reply} />
            </section>
        </div>

        <Card border>
            <div class="flex flex-col gap-4">
                <SectionHeading title="Contact" />

                <LabelValueList
                    items={[
                        { label: "Email", value: enquiry.email },
                        // As they typed it.
                        { label: "Phone", value: enquiry.phone }
                    ]}
                />
            </div>
        </Card>
    </div>
</Page>
