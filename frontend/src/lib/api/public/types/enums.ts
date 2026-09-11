import { z } from "zod";

export const stripeStatusSchema = z.enum([
  "PENDING",
  "SUCCEEDED",
  "FAILED",
]);

export type StripeStatus = 
	z.infer<typeof stripeStatusSchema>;


export const currencyCodeSchema = z.enum([
  "AUD",
  "NZD",
  "USD",
]);

export type CurrencyCode = 
	z.infer<typeof currencyCodeSchema>;


export const bookingStatusSchema = z.enum([
  "PENDING",
  "CONFIRMED",
  "CANCELLED",
  "EXPIRED",
]);

export type BookingStatus = 
	z.infer<typeof bookingStatusSchema>;


export const paymentStatusSchema = z.enum([
  "PENDING",
  "PAID",
  "REFUNDED",
  "FAILED",
]);

export type PaymentStatus = 
	z.infer<typeof paymentStatusSchema>;


export const childDocumentTypeSchema = z.enum([
  "medical_action_plan",
  "asthma_action_plan",
  "allergy_anaphylaxis_plan",
  "other",
]);

export type ChildDocumentType = z.infer<typeof childDocumentTypeSchema>;


export const childDocumentUploadStatusSchema = z.enum([
  "pending",
  "uploaded",
  "failed",
]);

export type ChildDocumentUploadStatus = 
	z.infer<typeof childDocumentUploadStatusSchema>;


export const medicalReviewStatusSchema = z.enum([
  "not_required",
  "pending",
  "documentation_requested",
  "approved",
]);

export type MedicalReviewStatus = 
	z.infer<typeof medicalReviewStatusSchema>;


export const serviceDayStatusSchema = z.enum([
    "AVAILABLE",
    "CLOSED",
    "FULL",
    "BOOKED",
    "UNAVAILABLE",
]);

export const ServiceDayStatus =
    serviceDayStatusSchema.enum;

export type ServiceDayStatus =
    z.infer<typeof serviceDayStatusSchema>;