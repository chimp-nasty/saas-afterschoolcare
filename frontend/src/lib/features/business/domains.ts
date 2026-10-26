import type { Tone } from '$lib/components/text/textSize';

import type { DomainResponse } from '$lib/api/schema';

// How each state of a custom domain is worded (Business settings › Domains;
// the states are described in backend/migrations/schema/0002_tenancy.sql).
export const DOMAIN_STATES: Record<DomainResponse['state'], { label: string; tone: Tone; help: string }> = {
	pending_dns: {
		label: 'Waiting for DNS',
		tone: 'warning',
		help: 'Add the records below where your domain is managed. Changes can take a few hours to show; we check every few minutes for 7 days.'
	},
	verified: {
		label: 'Setting up',
		tone: 'warning',
		help: "It's yours. Its certificate is being issued and it goes live once every record is found, usually within an hour."
	},
	active: {
		label: 'Live',
		tone: 'success',
		help: 'Working. Keep these records: renewing the certificate needs them.'
	},
	suspended: {
		label: 'Suspended',
		tone: 'danger',
		help: 'Its records went missing, so your site went back to its usual address. Put them back and it returns.'
	},
	failed: {
		label: 'Failed',
		tone: 'danger',
		help: 'Remove it and add it again to start over.'
	},
	removing: {
		label: 'Removing',
		tone: 'neutral',
		help: 'No longer used. It disappears from this list shortly.'
	}
};
