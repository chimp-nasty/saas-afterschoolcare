<script lang="ts">
    import { goto, invalidate } from "$app/navigation";
    import { toast } from "svelte-sonner";

    import Button from "$lib/components/actions/Button.svelte";
    import TabbedPanels from "$lib/components/controls/TabbedPanels.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import { confirmAction } from "$lib/components/overlays/confirm.svelte";
    import ChildDocumentList from "$lib/features/children/components/ChildDocumentList.svelte";
    import ChildDocumentUploadForm from "$lib/features/children/components/ChildDocumentUploadForm.svelte";
    import EditChildProfileForm from "$lib/features/children/components/EditChildProfileForm.svelte";
    import { DOCUMENT_TYPE_LABELS, fileContentType } from "$lib/features/children/documents";
    import { reviewNotice } from "$lib/features/children/review";
    import type { ChildDocumentUpload } from "$lib/features/children/types";

    import { createChildrenApi } from "$lib/api/public/adapters/children";
    import { createChildDocumentsApi } from "$lib/api/public/adapters/childDocuments";
    import { uploadToStorage } from "$lib/api/storage";
    import type { ApiResponse } from "$lib/api/wrapper";
    import type { ChildDocumentResponse, ChildResponse, UpdateChildRequest } from "$lib/api/schema";
    import { accountTabs, childTabs } from "$lib/navigation/tabs";

    let { data } = $props();

    const childrenApi = createChildrenApi();
    const documentsApi = createChildDocumentsApi();

    // Starts from the loader; a save replaces it with what the server
    // returns (including a review status the change may have reset).
    let child = $derived<ChildResponse>(data.child);

    let activeTab = $state<string>(childTabs.PROFILE);
    let uploadProgress = $state<number | null>(null);

    const tabs = [
        { id: childTabs.PROFILE, label: "Profile" },
        { id: childTabs.MANAGE_DOCUMENTS, label: "Docs" }
    ];

    const notice = $derived(reviewNotice(child.review_status, child.first_name));

    async function updateChild(body: UpdateChildRequest) {
        const response = await childrenApi.update(child.id, body);

        if (response.ok && response.data) {
            child = response.data;
        }

        return response;
    }

    // Refused (and explained in a toast) while the child has upcoming
    // bookings.
    async function removeChild() {
        await confirmAction({
            title: `Remove ${child.first_name}?`,
            message: `${child.first_name} will no longer appear in your account and can't be booked. Past bookings are kept. You can't remove a child with upcoming bookings.`,
            confirmLabel: "Remove child",
            tone: "danger",
            action: async () => {
                const response = await childrenApi.deactivate(child.id);

                if (response.ok) {
                    await invalidate("app:customer-account");
                    await goto(`/${data.locationCode}/account?state=${accountTabs.CHILDREN}`);
                }
            },
        });
    }

    // A response for a step that never reached the API (cancelled, or the
    // file didn't get to storage). The form keeps what was entered.
    function notSent(msg: string): ApiResponse<null> {
        return { ok: false, msg, data: null, status: 0, fieldErrors: {} };
    }

    // Start the upload, send the file straight to storage, then have the
    // server check and accept it. Accepting it sends the child to review.
    async function uploadDocument({ document_type, file }: ChildDocumentUpload) {
        if (child.review_status === "approved") {
            const confirmed = await confirmAction({
                title: `${child.first_name} will need reviewing again`,
                message: `Staff review new documents before ${child.first_name} can be booked again. Existing bookings aren't affected.`,
                confirmLabel: "Upload",
            });

            if (!confirmed) return notSent("Upload cancelled");
        }

        const started = await documentsApi.start({
            child_id: child.id,
            document_type,
            filename: file.name,
            content_type: fileContentType(file),
            size_bytes: file.size,
        });

        if (!started.ok || !started.data) return started;

        uploadProgress = 0;

        const sent = await uploadToStorage(
            started.data.upload,
            file,
            (percent) => (uploadProgress = percent)
        );

        uploadProgress = null;

        if (!sent) {
            const msg = "The file didn't upload. Check your connection and try again.";
            toast.error(msg);

            return notSent(msg);
        }

        const completed = await documentsApi.complete(started.data.document.id);

        if (completed.ok) {
            await invalidate("app:child");
        }

        return completed;
    }

    // The tab is opened before asking for the link, while the tap still
    // counts: phones block tabs opened after waiting on a request.
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

    async function removeDocument(document: ChildDocumentResponse) {
        await confirmAction({
            title: `Remove ${DOCUMENT_TYPE_LABELS[document.document_type].toLowerCase()}?`,
            message: `${document.filename} will no longer show here, and staff will review ${child.first_name}'s medical details again before new bookings. The centre keeps a copy for its records.`,
            confirmLabel: "Remove",
            tone: "danger",
            action: async () => {
                const response = await documentsApi.remove(document.id);

                if (response.ok) {
                    await invalidate("app:child");
                }
            },
        });
    }
</script>

<Page>
    <PageHeader title={`${child.first_name} ${child.last_name}`} />

    {#if notice}
        <Card border>
            <div class="flex flex-col gap-4">
                <p class="text-sm text-(--text-muted)">
                    {notice}
                </p>

                {#if child.review_status === "documentation_requested" && child.documentation_request}
                    <div class="flex flex-col gap-1">
                        <p class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">
                            What the centre needs
                        </p>

                        <p class="text-base text-(--text) whitespace-pre-line">
                            {child.documentation_request}
                        </p>
                    </div>

                    {#if activeTab !== childTabs.MANAGE_DOCUMENTS}
                        <Button
                            fullWidth
                            onclick={() => (activeTab = childTabs.MANAGE_DOCUMENTS)}
                        >
                            Upload documents
                        </Button>
                    {/if}
                {/if}
            </div>
        </Card>
    {/if}

    <TabbedPanels
        {tabs}
        initialTab={childTabs.PROFILE}
        bind:activeTab
        queryParam="state"
    >
        {#snippet panel(id)}
            {#if id === childTabs.PROFILE}
                <EditChildProfileForm
                    {child}
                    onsubmit={updateChild}
                />

                <Button
                    variant="ghost"
                    fullWidth
                    onclick={removeChild}
                >
                    Remove child
                </Button>
            {:else}
                <div class="flex flex-col gap-6">
                    <ChildDocumentList
                        documents={data.documents}
                        firstName={child.first_name}
                        onview={viewDocument}
                        onremove={removeDocument}
                    />

                    <div class="flex flex-col gap-4">
                        <h2 class="text-lg font-extrabold text-(--text)">
                            Add a document
                        </h2>

                        <ChildDocumentUploadForm
                            progress={uploadProgress}
                            onsubmit={uploadDocument}
                        />
                    </div>
                </div>
            {/if}
        {/snippet}
    </TabbedPanels>
</Page>
