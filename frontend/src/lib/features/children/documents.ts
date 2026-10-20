import type { ChildDocumentType } from '$lib/api/schema';

// How each document type reads to families and staff.
export const DOCUMENT_TYPE_LABELS: Record<ChildDocumentType, string> = {
    medical_action_plan: 'Medical action plan',
    asthma_action_plan: 'Asthma action plan',
    allergy_anaphylaxis_plan: 'Allergy or anaphylaxis plan',
    other: 'Other document'
};

// The file picker's filter. The server decides what's accepted (PDF, JPEG,
// PNG or HEIC, up to 10 MB); this only narrows what the picker shows.
export const DOCUMENT_ACCEPT = '.pdf,.jpg,.jpeg,.png,.heic,application/pdf,image/jpeg,image/png,image/heic';

const TYPES_BY_EXTENSION: Record<string, string> = {
    pdf: 'application/pdf',
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    png: 'image/png',
    heic: 'image/heic'
};

// Some browsers (e.g. for HEIC on Windows) give no type; fall back to the
// file name so the server can judge it.
export function fileContentType(file: File): string {
    if (file.type) return file.type;

    const extension = file.name.split('.').pop()?.toLowerCase() ?? '';

    return TYPES_BY_EXTENSION[extension] ?? 'application/octet-stream';
}

// "240 KB", "3.2 MB".
export function formatFileSize(bytes: number): string {
    if (bytes < 1024 * 1024) {
        return `${Math.max(1, Math.round(bytes / 1024))} KB`;
    }

    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
