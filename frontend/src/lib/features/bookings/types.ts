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
