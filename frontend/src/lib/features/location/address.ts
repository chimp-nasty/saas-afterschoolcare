import { PUBLIC_GOOGLE_MAPS_EMBED_KEY } from '$env/static/public';

import type { PublicLocationResponse } from '$lib/api/schema';

type Address = Pick<
    PublicLocationResponse,
    'address_line_1' | 'address_line_2' | 'suburb' | 'state' | 'postcode' | 'google_place_id'
>;

// ["1 Placeholder Street", "Brisbane City QLD 4000"]
export function addressLines(location: Address): string[] {
    return [
        location.address_line_1,
        location.address_line_2,
        `${location.suburb} ${location.state} ${location.postcode}`
    ].filter((line): line is string => Boolean(line));
}

// Opens the address in Google Maps (on phones, the maps app). Uses the
// exact place once addresses are geocoded (google_place_id).
export function mapsUrl(location: Address): string {
    const query = encodeURIComponent(`${addressLines(location).join(', ')}, Australia`);
    const place = location.google_place_id
        ? `&query_place_id=${encodeURIComponent(location.google_place_id)}`
        : '';

    return `https://www.google.com/maps/search/?api=1&query=${query}${place}`;
}

// The address on an embedded Google map (Maps Embed API, docs/public-site.md
// stage 10), or null without a key. It takes the address itself (or the
// exact place once geocoded), so nothing is geocoded first.
export function mapEmbedUrl(location: Address): string | null {
    if (!PUBLIC_GOOGLE_MAPS_EMBED_KEY) return null;

    const query = location.google_place_id
        ? `place_id:${location.google_place_id}`
        : `${addressLines(location).join(', ')}, Australia`;

    return `https://www.google.com/maps/embed/v1/place?key=${encodeURIComponent(PUBLIC_GOOGLE_MAPS_EMBED_KEY)}&q=${encodeURIComponent(query)}`;
}
