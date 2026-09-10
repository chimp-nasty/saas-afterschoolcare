import { z } from 'zod';

import {
    bookingStatusSchema,
    currencyCodeSchema,
    paymentStatusSchema,
} from './enums';


// Booking Selection

export const bookingSelectionSchema = z.object({
    child_id: z.uuid(),
    location_service_days: z.array(z.uuid())
});

export type BookingSelection =
    z.infer<typeof bookingSelectionSchema>;


// Create Booking

export const createBookingRequestSchema = z.object({
    idempotency_key: z.string(),
    bookings: z.array(bookingSelectionSchema)
});

export type CreateBookingRequest =
    z.infer<typeof createBookingRequestSchema>;


export const createBookingResponseSchema = z.object({
    idempotency_key: z.string(),
    amount: z.number(),
    booking_group_id: z.uuid()
});

export type CreateBookingResponse =
    z.infer<typeof createBookingResponseSchema>;


// Booking Conflict

export const bookingConflictRowSchema = z.object({
    child_id: z.uuid(),
    child_name: z.string(),
    location_service_day_id: z.uuid(),
    location_service_date: z.string()
});

export type BookingConflictRow =
    z.infer<typeof bookingConflictRowSchema>;


// Booking Filters

export const listBookingsFilterRequestSchema = z.object({
    booking_status: bookingStatusSchema
        .nullable()
        .optional(),

    payment_status: paymentStatusSchema
        .nullable()
        .optional(),

    date_from: z.string().nullable().optional(),
    date_to: z.string().nullable().optional()
});

export type ListBookingsFilterRequest =
    z.infer<typeof listBookingsFilterRequestSchema>;


// Booking Response

export const bookingResponseSchema = z.object({
    id: z.uuid(),
    location_id: z.uuid(),
    user_id: z.uuid(),
    booking_group_id: z.uuid(),
    location_service_day_id: z.uuid(),
    child_id: z.uuid(),

    child_name: z.string(),
    service_date: z.string(),
    service_name: z.string(),

    booking_status: bookingStatusSchema,
    payment_status: paymentStatusSchema,
    cancelled_at: z.string().nullable(),

    price_snapshot_cents: z.number(),
    currency: currencyCodeSchema,

    created_at: z.string(),
    updated_at: z.string()
});

export type BookingResponse =
    z.infer<typeof bookingResponseSchema>;


// Booking Table Response

export const bookingTableResponseSchema = z.object({
    id: z.uuid(),
    location_id: z.uuid(),
    user_id: z.uuid(),
    booking_group_id: z.uuid(),
    location_service_day_id: z.uuid(),
    child_id: z.uuid(),

    child_name: z.string(),
    service_date: z.string(),
    service_name: z.string(),

    booking_status: bookingStatusSchema,
    payment_status: paymentStatusSchema
});

export type BookingTableResponse =
    z.infer<typeof bookingTableResponseSchema>;