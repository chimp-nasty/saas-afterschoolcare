import type { MedicalReviewStatus } from '$lib/api/schema';

// How a child's medical review status reads to a family.
export const REVIEW_STATUS_LABELS: Record<MedicalReviewStatus, string> = {
    not_required: 'Not needed',
    pending: 'With staff for review',
    documentation_requested: 'Documents needed',
    approved: 'Approved'
};

// What the family is told on the child's page while a review is open.
export function reviewNotice(
    status: MedicalReviewStatus,
    firstName: string
): string | null {
    switch (status) {
        case 'pending':
            return `Staff are reviewing ${firstName}'s medical details. ${firstName} can't be booked until they're approved. Existing bookings aren't affected.`;
        case 'documentation_requested':
            return `The centre needs documents before ${firstName} can be booked. Upload them under Docs.`;
        default:
            return null;
    }
}
