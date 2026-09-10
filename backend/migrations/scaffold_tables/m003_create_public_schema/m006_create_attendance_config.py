from sqlalchemy import text
from sqlalchemy.engine import Connection


def up(conn: Connection) -> None:
    conn.execute(text("""
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
    """))

    conn.execute(text("""
        -- =====================================================
        -- ATTENDANCE RECORDS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.attendance_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            booking_id UUID NOT NULL UNIQUE
                REFERENCES public.bookings(id)
                ON DELETE CASCADE,

            signed_in_at TIMESTAMPTZ,
            signed_out_at TIMESTAMPTZ,

            signed_in_by_user_id UUID
                REFERENCES auth.users(id),

            signed_out_by_user_id UUID
                REFERENCES auth.users(id),

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT attendance_signout_requires_signin
                CHECK (
                    signed_out_at IS NULL
                    OR signed_in_at IS NOT NULL
                ),

            CONSTRAINT attendance_signout_after_signin
                CHECK (
                    signed_out_at IS NULL
                    OR signed_out_at >= signed_in_at
                )
        );

        
        -- =====================================================
        -- ACTIONS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.actions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            user_id UUID NOT NULL
                REFERENCES auth.users(id)
                ON DELETE CASCADE,
                
            child_id UUID
                REFERENCES public.child_profile(id)
                ON DELETE CASCADE,

            target TEXT NOT NULL,
            
            title TEXT NOT NULL,
            message TEXT NOT NULL,

            created_by_user_id UUID NOT NULL
                REFERENCES auth.users(id),

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            cited_at TIMESTAMPTZ
        );
    """))