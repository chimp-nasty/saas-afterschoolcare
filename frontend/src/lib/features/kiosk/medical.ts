import type { MedicalReviewStatus } from '$lib/api/schema';

// How a child's medical review reads at the staff kiosk. Children on the run
// sheet were approved before they could be booked, so "pending" there means
// the family changed something since (docs/portals.md).
export const KIOSK_REVIEW_STATUS: Record<MedicalReviewStatus, { label: string; reviewed: boolean }> = {
	approved: { label: 'Approved by admin', reviewed: true },
	not_required: { label: 'No medical review needed', reviewed: true },
	pending: { label: 'Not yet reviewed by admin', reviewed: false },
	documentation_requested: { label: 'Not yet reviewed by admin (documents requested)', reviewed: false }
};

// Opens a document in a new tab with the tablet's own viewer, which also
// prints. The tab is opened straight away (in the tap), then pointed at the
// link once it arrives, so it isn't blocked as a pop-up.
export async function openDocument(link: () => Promise<string | null>): Promise<string | null> {
	const tab = window.open('', '_blank');
	const url = await link();

	if (!tab) return 'The tablet blocked the new tab. Allow pop-ups for this site.';

	if (!url) {
		tab.close();
		return "That document couldn't be opened. Please try again.";
	}

	tab.opener = null;
	tab.location.href = url;

	return null;
}
