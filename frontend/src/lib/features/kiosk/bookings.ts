import type { FamilyBookingResponse, PaymentStatus } from '$lib/api/schema';

// How a booking's payment reads to staff at the kiosk.
export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
	PENDING: 'Awaiting payment',
	PAID: 'Paid',
	REFUNDED: 'Refunded',
	FAILED: 'Payment failed'
};

// The payment column: a refund that's been asked for but not yet settled
// shows as requested.
export function paymentLabel(booking: FamilyBookingResponse): string {
	if (booking.refund_status === 'PENDING') return 'Refund requested';

	return PAYMENT_STATUS_LABELS[booking.payment_status];
}
