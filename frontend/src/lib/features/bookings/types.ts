// Computed in the browser by ServiceDayCalendar; the backend doesn't send it.
export const ServiceDayStatus = {
    AVAILABLE: 'AVAILABLE',
    CLOSED: 'CLOSED',
    FULL: 'FULL',
    BOOKED: 'BOOKED',
    UNAVAILABLE: 'UNAVAILABLE',
} as const;

export type ServiceDayStatus =
    typeof ServiceDayStatus[keyof typeof ServiceDayStatus];

// "My bookings" page size (bookings/+page.ts loads the first page, the page
// appends the rest).
export const BOOKING_GROUPS_PAGE_SIZE = 20;
