// Worked out in the browser by ServiceDayCalendar, from the day's data and
// the children currently selected; the backend doesn't send it.
export const ServiceDayStatus = {
    AVAILABLE: 'AVAILABLE',
    // Bookable, but LOW_PLACES_THRESHOLD places or fewer left.
    LOW: 'LOW',
    // A selected child already has this day.
    BOOKED: 'BOOKED',
    // Fewer places left than children selected.
    FULL: 'FULL',
    CLOSED: 'CLOSED',
    // Today or earlier.
    PAST: 'PAST',
    // No session that day.
    UNAVAILABLE: 'UNAVAILABLE',
} as const;

// At or below this, a day shows how many places are left.
export const LOW_PLACES_THRESHOLD = 3;

export type ServiceDayStatus =
    typeof ServiceDayStatus[keyof typeof ServiceDayStatus];

// "My bookings" page size, per tab (bookings/+page.ts loads each tab's
// first page, the page appends the rest).
export const BOOKING_GROUPS_PAGE_SIZE = 20;
