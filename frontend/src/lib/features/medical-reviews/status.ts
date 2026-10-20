import type { MedicalReviewStatus } from '$lib/api/schema';

// How a child's medical review status reads to staff. Families see
// features/children/review.ts instead.
export const STAFF_REVIEW_STATUS_LABELS: Record<MedicalReviewStatus, string> = {
    not_required: 'No review needed',
    pending: 'Waiting for review',
    documentation_requested: 'Documents requested',
    approved: 'Approved'
};
