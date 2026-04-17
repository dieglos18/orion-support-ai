"""
Unit tests for Pydantic schemas.
Ensures data contracts are enforced.
"""
import pytest
from pydantic import ValidationError
from src.schemas.ticket import SupportTicket, AIAnalysis


def test_support_ticket_valid():
    """Valid ticket should pass validation"""
    ticket = SupportTicket(
        ticket_id="TKT-2024-001",
        customer_email="user@example.com",
        subject="Login issue",
        content="I cannot access my account after password reset"
    )
    assert ticket.ticket_id == "TKT-2024-001"
    assert ticket.customer_email == "user@example.com"


def test_support_ticket_invalid_email():
    """Invalid email should fail validation"""
    with pytest.raises(ValidationError):
        SupportTicket(
            ticket_id="TKT-001",
            customer_email="not-an-email",  # Invalid
            subject="Test",
            content="Test content here"
        )


def test_ai_analysis_valid():
    """Valid analysis should pass validation"""
    analysis = AIAnalysis(
        category="Technical",
        urgency=4,
        reasoning="The user is experiencing login issues which block access",
        suggested_reply="Hello! I understand you're having trouble logging in..."
    )
    assert analysis.category == "Technical"
    assert analysis.urgency == 4


def test_ai_analysis_invalid_urgency():
    """Urgency out of range should fail"""
    with pytest.raises(ValidationError):
        AIAnalysis(
            category="Technical",
            urgency=10,  # Invalid (must be 1-5)
            reasoning="Test reasoning",
            suggested_reply="Test reply"
        )


def test_ai_analysis_invalid_category():
    """Invalid category should fail"""
    with pytest.raises(ValidationError):
        AIAnalysis(
            category="InvalidCategory",  # Not in Literal options
            urgency=3,
            reasoning="Test reasoning",
            suggested_reply="Test reply"
        )