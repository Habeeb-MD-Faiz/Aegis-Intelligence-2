"""
Request bodies for the x402 routes.

Only the shapes the API actually binds live here. Two more once described
protocol responses that the code never constructed or validated — the routes
return plain dicts from payment_service — so they documented nothing and
validated nothing.
"""

from pydantic import BaseModel


class PaymentRequest(BaseModel):
    request_id: str
    task: str
    provider: str
    api: str
    amount: float
    currency: str = "USDC"


class PaymentAuthorization(BaseModel):
    request_id: str
    payment_signature: str
