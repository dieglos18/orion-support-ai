"""
Integration tests for the LangGraph workflow.
Requires AWS credentials and Bedrock access.
"""
import pytest
from agents.workflow import process_ticket


@pytest.fixture
def sample_ticket():
    """Sample technical support ticket"""
    return {
        "ticket_id": "TEST-001",
        "customer_email": "user@example.com",
        "subject": "Cannot login after password reset",
        "content": "I tried to reset my password but now I can't login. "
                   "The error message says 'Invalid credentials' even though "
                   "I just set a new password 5 minutes ago."
    }


@pytest.mark.integration
def test_workflow_end_to_end(sample_ticket):
    """
    Test complete workflow execution.

    This will make real API calls to Amazon Bedrock (cost is low with Nova Micro).
    """
    # Run workflow
    result = process_ticket(sample_ticket)

    # Verify state structure
    assert 'ticket' in result
    assert 'triage_result' in result
    assert 'draft_response' in result
    assert 'validation_result' in result
    assert 'final_analysis' in result

    # Verify triage
    triage = result['triage_result']
    assert triage['category'] in ['Technical', 'Billing', 'Account', 'General']
    assert 1 <= triage['urgency'] <= 5
    assert len(triage['reasoning']) > 20

    # Verify response
    draft = result['draft_response']
    assert len(draft['suggested_reply']) >= 50
    assert isinstance(draft['requires_human_review'], bool)

    # Verify validation
    validation = result['validation_result']
    assert 'validation_score' in validation
    assert 'passed' in validation

    # Verify final analysis (Pydantic schema)
    analysis = result['final_analysis']
    assert analysis['category'] == triage['category']
    assert analysis['urgency'] == triage['urgency']

    # Verify cost tracking
    assert 'total_cost' in result
    assert result['total_cost'] > 0

    print("\n✅ Workflow test passed!")
    print(f"Category: {analysis['category']}")
    print(f"Urgency: {analysis['urgency']}")
    print(f"Cost: ${result['total_cost']:.6f}")


@pytest.mark.integration
def test_workflow_with_critical_ticket():
    """Test workflow handles critical urgency correctly"""
    critical_ticket = {
        "ticket_id": "CRIT-001",
        "customer_email": "admin@company.com",
        "subject": "URGENT: Data loss after system crash",
        "content": "Our entire production database seems to be corrupted "
                   "after the server crash. We've lost customer orders from "
                   "the last 24 hours. This is a critical emergency."
    }

    result = process_ticket(critical_ticket)

    # Should be classified as critical
    assert result['triage_result']['urgency'] >= 4

    # Should require human review
    assert result['draft_response']['requires_human_review'] is True
