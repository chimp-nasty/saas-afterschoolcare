import type { StripeAccountStatusResponse } from '$lib/api/schema';
import type { Tone } from '$lib/components/text/textSize';

// How the business's Stripe account stands, in one line: the same words on
// a centre's Admin › Payments and in Business settings › Payments.
export function stripeStanding(account: StripeAccountStatusResponse | null): { tone: Tone; text: string } {
	if (!account?.connected) {
		return { tone: 'warning', text: "Stripe isn't connected. Families can't book until it is." };
	}

	if (account.revoked) {
		return { tone: 'danger', text: 'This Stripe account no longer gives us access. Connect Stripe again to take bookings; refund past payments in your Stripe dashboard.' };
	}

	if (account.disconnected) {
		return { tone: 'warning', text: "Online payments are turned off, so families can't book. Past payments can still be refunded." };
	}

	if (!account.takes_payments && account.is_linked) {
		return { tone: 'warning', text: "Your Stripe account isn't ready to take payments yet. Finish setting it up in your Stripe dashboard, then refresh the status here." };
	}

	if (!account.takes_payments) {
		return { tone: 'warning', text: 'Stripe setup isn\'t finished. Families can book once Stripe has everything it needs.' };
	}

	return { tone: 'success', text: 'Taking bookings. Families pay into your Stripe account.' };
}
