export type BookingSelection = {
    child_id: string
    location_service_days: string[]
}

export type CreateBookingRequest = {
    idempotency_key: string
    bookings: BookingSelection[]
}

export type CreateBookingResponse = {
    idempotency_key: string
    amount: number
    booking_group_id: string
}

export type BookingConflictRow = {
    child_id: string
    child_name: string
    location_service_day_id: string
    location_service_date: string
}

export type ListBookingsFilterRequest = {
    booking_status?: string[] | null
    payment_status?: string[] | null
    date_from?: string | null
    date_to?: string | null
}

export type BookingResponse = {
    id: string
    location_id: string
    user_id: string
    booking_group_id: string
    location_service_day_id: string
    child_id: string

    child_name: string
    service_date: string
    service_name: string

    booking_status: string
    payment_status: string
    cancelled_at: string | null

    price_snapshot_cents: number
    currency: string

    created_at: string
    updated_at: string
}

export type BookingTableResponse = {
    id: string
    location_id: string
    user_id: string
    booking_group_id: string
    location_service_day_id: string
    child_id: string

    child_name: string
    service_date: string
    service_name: string

    booking_status: string
    payment_status: string
}