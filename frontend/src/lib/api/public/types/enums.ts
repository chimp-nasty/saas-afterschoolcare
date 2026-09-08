export enum StripeStatus {
	PENDING = 'PENDING',
	SUCCEEDED = 'SUCCEEDED',
	FAILED = 'FAILED'
}

export enum CurrencyCode {
	AUD = 'AUD',
	NZD = 'NZD',
	USD = 'USD'
}

export enum BookingStatus {
	PENDING = 'PENDING',
	CONFIRMED = 'CONFIRMED',
	CANCELLED = 'CANCELLED',
	EXPIRED = 'EXPIRED'
}

export enum PaymentStatus {
	PENDING = 'PENDING',
	PAID = 'PAID',
	REFUNDED = 'REFUNDED',
	FAILED = 'FAILED'
}

export enum ChildDocumentType {
	MEDICAL_ACTION_PLAN = 'medical_action_plan',
	ASTHMA_ACTION_PLAN = 'asthma_action_plan',
	ALLERGY_ANAPHYLAXIS_PLAN = 'allergy_anaphylaxis_plan',
	OTHER = 'other'
}

export enum ChildDocumentUploadStatus {
	PENDING = 'pending',
	UPLOADED = 'uploaded',
	FAILED = 'failed'
}

export enum MedicalReviewStatus {
	NOT_REQUIRED = 'not_required',
	PENDING = 'pending',
	DOCUMENTATION_REQUESTED = 'documentation_requested',
	APPROVED = 'approved'
}

export enum ServiceDayStatus {
    AVAILABLE = 'AVAILABLE',
    CLOSED = 'CLOSED',
    FULL = 'FULL',
    BOOKED = 'BOOKED',
    UNAVAILABLE = 'UNAVAILABLE'
}