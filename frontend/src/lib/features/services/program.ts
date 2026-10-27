// A service's program text (docs/public-site.md, section 4): the parts
// after its description, in the order the programs page shows them, with
// their headings. Shared by the page and its inline editor.
import type { LocationServiceSelectionResponse } from '$lib/api/schema';

export type ProgramField = 'inclusions' | 'drop_off_pickup' | 'what_to_bring' | 'activities';

export const PROGRAM_FIELDS: { field: ProgramField; label: string }[] = [
	{ field: 'inclusions', label: "What's included" },
	{ field: 'drop_off_pickup', label: 'Drop-off and pickup' },
	{ field: 'what_to_bring', label: 'What to bring' },
	{ field: 'activities', label: 'Activities' }
];

// The parts this service has written, in order.
export function programParts(
	service: LocationServiceSelectionResponse
): { field: ProgramField; label: string; text: string }[] {
	return PROGRAM_FIELDS.flatMap(({ field, label }) => {
		const text = service[field];

		return text ? [{ field, label, text }] : [];
	});
}

// Whether the program has any text beyond its settings.
export function hasProgramText(service: LocationServiceSelectionResponse): boolean {
	return Boolean(service.description) || programParts(service).length > 0;
}
