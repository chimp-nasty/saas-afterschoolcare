from pydantic import BaseModel


class PaymentCheckResponse(BaseModel):
    payments_checked: int
