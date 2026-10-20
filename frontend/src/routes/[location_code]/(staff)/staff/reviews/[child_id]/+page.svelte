<script lang="ts">
    import { goto } from "$app/navigation";
    import { toast } from "svelte-sonner";

    import ActionBar from "$lib/components/actions/ActionBar.svelte";
    import Button from "$lib/components/actions/Button.svelte";
    import HyperTextLink from "$lib/components/actions/HyperTextLink.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import DataCard from "$lib/components/layout/DataCard.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import { confirmAction } from "$lib/components/overlays/confirm.svelte";
    import ChildDocumentList from "$lib/features/children/components/ChildDocumentList.svelte";
    import DocumentationRequestForm from "$lib/features/medical-reviews/components/DocumentationRequestForm.svelte";
    import { STAFF_REVIEW_STATUS_LABELS } from "$lib/features/medical-reviews/status";

    import { createChildDocumentsApi } from "$lib/api/public/adapters/childDocuments";
    import { createMedicalReviewsApi } from "$lib/api/public/adapters/medicalReviews";
    import type { ChildDocumentResponse } from "$lib/api/schema";
    import { formatDateOfBirth, formatPhone, formatTimestampDDMMYYYY } from "$lib/utils/helpers";

    let { data } = $props();

    const reviewsApi = createMedicalReviewsApi();
    const documentsApi = createChildDocumentsApi();

    const review = $derived(data.review);
    const listHref = $derived(`/${data.locationCode}/staff/reviews`);

    // A removed child can't be reviewed (the API refuses too).
    const canDecide = $derived(review.is_active);

    async function approve() {
        await confirmAction({
            title: `Approve ${review.first_name}?`,
            message: `${review.first_name} can be booked again, and the family is told. Approve only once you've read the medical details and any documents.`,
            confirmLabel: "Approve",
            action: async () => {
                const response = await reviewsApi.decide(review.child_id, { decision: "approved" });

                if (response.ok) {
                    await goto(listHref, { invalidateAll: true });
                }
            },
        });
    }

    async function requestDocuments({ message }: { message: string }) {
        const response = await reviewsApi.decide(review.child_id, {
            decision: "documentation_requested",
            message,
        });

        if (response.ok) {
            await goto(`${listHref}?state=requested`, { invalidateAll: true });
        }

        return response;
    }

    // The tab is opened before asking for the link, while the tap still
    // counts: tablets block tabs opened after waiting on a request.
    async function viewDocument(document: ChildDocumentResponse) {
        const tab = window.open("", "_blank");

        const response = await documentsApi.download(document.id);

        if (!response.ok || !response.data) {
            tab?.close();
            toast.error(response.msg || "This document couldn't be opened.");
            return;
        }

        if (tab) {
            tab.opener = null;
            tab.location.href = response.data.url;
        } else {
            window.location.href = response.data.url;
        }
    }
</script>

<Page width="wide">
    <HyperTextLink href={listHref}>Back to medical reviews</HyperTextLink>

    <PageHeader
        eyebrow="Medical review"
        title={`${review.first_name} ${review.last_name}`}
        description={`${STAFF_REVIEW_STATUS_LABELS[review.review_status]} since ${formatTimestampDDMMYYYY(review.status_since)}`}
    />

    {#if !review.is_active}
        <Card border>
            <p class="text-sm text-(--text-muted)">
                This child has been removed by their family, so there's nothing to review.
            </p>
        </Card>
    {/if}

    {#if review.documentation_request}
        <Card border>
            <div class="flex flex-col gap-1">
                <p class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">
                    {review.review_status === "documentation_requested"
                        ? "Requested from the family"
                        : "Last requested from the family"}
                </p>

                <p class="text-base text-(--text) whitespace-pre-line">
                    {review.documentation_request}
                </p>
            </div>
        </Card>
    {/if}

    <div class="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div class="flex flex-col gap-6">
            <DataCard
                title="Medical details"
                data={[
                    { label: "Date of birth", value: formatDateOfBirth(review.dob) },
                    { label: "Medical conditions", value: review.medical_info },
                    { label: "Allergies", value: review.allergy_info },
                    { label: "Medication", value: review.medication_info },
                ]}
            />

            <DataCard
                title="Family"
                data={[
                    { label: "Account holder", value: `${review.family_first_name} ${review.family_last_name}` },
                    { label: "Phone", value: review.family_phone ? formatPhone(review.family_phone) : null },
                    { label: "Email", value: review.family_email },
                ]}
            />
        </div>

        <section class="flex flex-col gap-4">
            <h2 class="text-lg font-extrabold text-(--text)">
                Documents
            </h2>

            <ChildDocumentList
                documents={data.documents}
                firstName={review.first_name}
                onview={viewDocument}
                empty="The family hasn't uploaded any documents."
            />
        </section>
    </div>

    {#if canDecide}
        <section class="flex flex-col gap-4">
            <h2 class="text-lg font-extrabold text-(--text)">
                Decision
            </h2>

            {#if review.review_status !== "approved"}
                <Card border>
                    <div class="flex flex-col gap-4">
                        <p class="text-sm text-(--text-muted)">
                            The details and documents are enough to care for {review.first_name} safely.
                        </p>

                        <ActionBar>
                            <Button onclick={approve}>
                                Approve
                            </Button>
                        </ActionBar>
                    </div>
                </Card>
            {/if}

            <DocumentationRequestForm
                firstName={review.first_name}
                onsubmit={requestDocuments}
            />
        </section>
    {/if}
</Page>
