import type { ChildDocumentType } from '$lib/api/schema';

// What the upload form hands the page; the page turns it into the
// three-step upload (start, send to storage, complete).
export type ChildDocumentUpload = {
    document_type: ChildDocumentType;
    file: File;
};
