import type { BookingStatus } from '$lib/api/schema';

// How a booking (or booking group) status reads to a customer.
export const BOOKING_STATUS_LABELS: Record<BookingStatus, string> = {
    PENDING: 'Awaiting payment',
    CONFIRMED: 'Confirmed',
    EXPIRED: 'Expired',
    CANCELLED: 'Cancelled'
};
