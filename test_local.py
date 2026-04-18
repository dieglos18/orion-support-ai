#!/usr/bin/env python3
"""
Local test script for workflow validation.
Run this before deploying to AWS.
"""
import json
import sys
import os
import traceback

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agents.workflow import process_ticket


def test_workflow_locally():
    """Test the workflow with a sample ticket"""
    
    print("🚀 Testing AI Support Orchestrator locally...\n")
    
    # Sample ticket
    ticket = {
        "ticket_id": "LOCAL-TEST-001",
        "customer_email": "test@example.com",
        "subject": "Login problem",
        "content": "I can't login to my account. Keep getting error message."
    }
    
    print(f"📨 Input Ticket:")
    print(json.dumps(ticket, indent=2))
    print("\n" + "="*60 + "\n")
    
    try:
        # Process ticket
        print("🤖 Running LangGraph workflow...\n")
        result = process_ticket(ticket)
        
        # Display results
        print("✅ Processing Complete!\n")
        print("📊 Triage Result:")
        print(json.dumps(result['triage_result'], indent=2))
        print()
        
        print("💬 Draft Response:")
        print(result['draft_response']['suggested_reply'])
        print()
        
        print("✓ Validation:")
        validation = result['validation_result']
        print(f"Score: {validation['validation_score']}/10")
        print(f"Passed: {validation['passed']}")
        print()
        
        print("💰 Cost Analysis:")
        print(f"Total cost: ${result.get('total_cost', 0):.6f}")
        
        # Token usage
        usage = result.get('usage_stats', {})
        total_in = sum(u.get('input_tokens', 0) for u in usage.values() if isinstance(u, dict))
        total_out = sum(u.get('output_tokens', 0) for u in usage.values() if isinstance(u, dict))
        print(f"Tokens: {total_in} input, {total_out} output")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_workflow_locally()
    sys.exit(0 if success else 1)
