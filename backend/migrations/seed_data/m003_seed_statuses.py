from sqlalchemy import text
from sqlalchemy.engine import Connection


def up(conn: Connection) -> None:
    conn.execute(text("""
        INSERT INTO public.booking_statuses (
            code,
            label,
            description
        )
        VALUES
            (
                'booked',
                'Booked',
                'The booking has been confirmed.'
            ),
            (
                'cancelled',
                'Cancelled',
                'The booking has been cancelled.'
            ),
            (
                'held',
                'Held',
                'The booking is temporarily reserved.'
            ),
            (
                'expired',
                'Expired',
                'The temporary booking hold has expired.'
            )
        ON CONFLICT (code)
        DO UPDATE SET
            label = EXCLUDED.label,
            description = EXCLUDED.description;


        INSERT INTO public.payment_statuses (
            code,
            label,
            description
        )
        VALUES
            (
                'pending',
                'Pending',
                'Payment has not yet been completed.'
            ),
            (
                'paid',
                'Paid',
                'Payment has been completed successfully.'
            ),
            (
                'failed',
                'Failed',
                'The payment attempt was unsuccessful.'
            ),
            (
                'refunded',
                'Refunded',
                'The payment has been refunded.'
            ),
            (
                'overdue',
                'Overdue',
                'Payment is overdue.'
            )
        ON CONFLICT (code)
        DO UPDATE SET
            label = EXCLUDED.label,
            description = EXCLUDED.description;


        INSERT INTO public.invoice_statuses (
            code,
            label,
            description
        )
        VALUES
            (
                'draft',
                'Draft',
                'The invoice has been created but not issued.'
            ),
            (
                'issued',
                'Issued',
                'The invoice has been issued to the customer.'
            ),
            (
                'paid',
                'Paid',
                'The invoice has been paid in full.'
            ),
            (
                'void',
                'Void',
                'The invoice has been voided.'
            ),
            (
                'refunded',
                'Refunded',
                'The invoice payment has been refunded.'
            ),
            (
                'overdue',
                'Overdue',
                'The invoice has passed its payment due date.'
            ),
            (
                'failed',
                'Failed',
                'Processing of the invoice or its payment failed.'
            )
        ON CONFLICT (code)
        DO UPDATE SET
            label = EXCLUDED.label,
            description = EXCLUDED.description;


        INSERT INTO public.medical_review_statuses (
            code,
            label,
            description
        )
        VALUES
            (
                'not_required',
                'Not Required',
                'No medical review is currently required.'
            ),
            (
                'review_required',
                'Review Required',
                'The child requires a medical information review.'
            ),
            (
                'awaiting_documents',
                'Awaiting Documents',
                'Required medical documentation has not yet been provided.'
            ),
            (
                'cleared',
                'Cleared',
                'The medical review has been completed and cleared.'
            ),
            (
                'not_cleared',
                'Not Cleared',
                'The medical review has been completed but clearance was not granted.'
            )
        ON CONFLICT (code)
        DO UPDATE SET
            label = EXCLUDED.label,
            description = EXCLUDED.description;
    """))