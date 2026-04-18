"""
Data contracts for the AI Support Orchestrator.
All input/output types are validated using Pydantic to prevent hallucinations.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Literal
from datetime import datetime


class SupportTicket(BaseModel):
    """
    Input schema: Raw ticket from customer.

    Example:
        {
            "ticket_id": "TKT-2024-001",
            "customer_email": "user@example.com",
            "subject": "Cannot login to my account",
            "content": "I've been trying to reset my password but..."
        }
    """
    ticket_id: str = Field(
        ...,
        description="Unique identifier for the ticket",
        min_length=5,
        max_length=50
    )
    customer_email: EmailStr = Field(
        ...,
        description="Customer's verified email address"
    )
    subject: str = Field(
        ...,
        description="Brief summary of the issue",
        min_length=5,
        max_length=200
    )
    content: str = Field(
        ...,
        description="Full description of the customer's issue",
        min_length=10,
        max_length=5000
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the ticket was created"
    )


class AIAnalysis(BaseModel):
    """
    Output schema: AI-generated ticket analysis.

    This enforces structured output from the LLM to prevent:
    - Hallucinated categories
    - Invalid urgency levels
    - Missing reasoning

    Example:
        {
            "category": "Technical",
            "urgency": 4,
            "reasoning": "Login issues affect user access...",
            "suggested_reply": "Hello! I understand you're having..."
        }
    """
    category: Literal["Technical", "Billing", "General", "Account"] = Field(
        ...,
        description="Issue category (must be one of the predefined types)"
    )
    urgency: int = Field(
        ...,
        ge=1,
        le=5,
        description="Urgency level: 1=Low, 5=Critical"
    )
    reasoning: str = Field(
        ...,
        description="Chain-of-Thought explanation for the classification",
        min_length=20,
        max_length=500
    )
    suggested_reply: str = Field(
        ...,
        description="Draft response for the customer",
        min_length=50,
        max_length=2000
    )
    requires_human_review: bool = Field(
        default=False,
        description="True if the AI is uncertain and needs human validation"
    )


class EventBridgeEvent(BaseModel):
    """
    Schema for critical ticket alerts sent to EventBridge.
    """
    ticket_id: str
    urgency: int
    category: str
    customer_email: EmailStr
    analysis_summary: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
