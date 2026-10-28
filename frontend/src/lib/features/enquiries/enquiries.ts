import type { EnquiryResponse, SubmitEnquiryRequest } from '$lib/api/schema';
import type { Tone } from '$lib/components/text/textSize';

export type EnquiryTopic = SubmitEnquiryRequest['topic'];
export type EnquiryStatus = EnquiryResponse['status'];

// The topics the contact form offers, in order.
export const ENQUIRY_TOPICS: EnquiryTopic[] = ['enrolment', 'bookings', 'general'];

// The words for an enquiry's topic and status, everywhere they're shown.
export const ENQUIRY_TOPIC_LABELS: Record<EnquiryTopic, string> = {
	enrolment: 'Enrolment',
	bookings: 'Bookings',
	general: 'General question'
};

export const ENQUIRY_STATUS_LABELS: Record<EnquiryStatus, string> = {
	new: 'New',
	replied: 'Replied',
	closed: 'Closed'
};

export const ENQUIRY_STATUS_TONES: Record<EnquiryStatus, Tone> = {
	new: 'warning',
	replied: 'success',
	closed: 'neutral'
};
