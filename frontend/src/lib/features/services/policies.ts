import type { LocationServiceSelectionResponse } from '$lib/api/schema';
import { formatMoney, formatTime } from '$lib/utils/helpers';

// What families are told about a service, worded once from its config so
// the landing page, booking and review always say the same thing.

type Service = LocationServiceSelectionResponse;

// "Ages 8–17", or the service's own wording when it has one ("Years 7 to 12").
export function agesLabel(service: Pick<Service, 'min_child_age' | 'max_child_age' | 'age_label'>): string {
    return service.age_label ?? `Ages ${service.min_child_age}–${service.max_child_age}`;
}

// The family's refund window (staff can refund later, until the session day).
export function refundPolicy(refundCutoffDays: number): string {
    if (refundCutoffDays === 0) {
        return 'Refundable up to and including the day of each session.';
    }

    if (refundCutoffDays === 1) {
        return 'Refundable until the day before each session.';
    }

    return `Refundable until ${refundCutoffDays} days before each session.`;
}

// "A $25.00 late fee applies for collection after 6:00pm (5 minutes' grace)."
// Null when the service has no late fee.
export function latePolicy(
    service: Pick<Service, 'late_fee_cents' | 'late_fee_grace_minutes' | 'end_time' | 'currency'>
): string | null {
    if (service.late_fee_cents === 0) {
        return null;
    }

    const fee = formatMoney(service.late_fee_cents, service.currency);
    const grace = service.late_fee_grace_minutes;
    const graceText = grace > 0 ? ` (${grace} ${grace === 1 ? "minute's" : "minutes'"} grace)` : '';

    return `A ${fee} late fee applies for collection after ${formatTime(service.end_time)}${graceText}.`;
}
