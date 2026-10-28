import type { SubmitPlatformEnquiryRequest } from '$lib/api/schema';

export type PlatformEnquiryTopic = SubmitPlatformEnquiryRequest['topic'];

// What a platform enquiry is about, worded once for the form and the
// console (docs/platform-site.md).
export const PLATFORM_ENQUIRY_TOPICS: Record<PlatformEnquiryTopic, string> = {
	own_business: 'Using this software for my own business',
	build_software: 'Having software like this built'
};
