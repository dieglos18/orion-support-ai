#!/usr/bin/env python3
"""
Script to send test tickets to SQS for end-to-end testing.
"""
import json
import sys
import boto3
from datetime import datetime, timezone


def send_ticket_to_sqs(queue_url: str, ticket_data: dict):
    """Send a test ticket to the SQS queue"""
    sqs = boto3.client('sqs')
    
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(ticket_data)
    )
    
    print(f"✅ Ticket sent to SQS")
    print(f"Message ID: {response['MessageId']}")
    return response


def main():
    # Get queue URL from Terraform output
    # Run: terraform output -raw sqs_queue_url
    queue_url = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not queue_url:
        print("Usage: python send_test_ticket.py <SQS_QUEUE_URL>")
        print("\nGet queue URL from Terraform:")
        print("  cd infra && terraform output -raw sqs_queue_url")
        sys.exit(1)
    
    # Sample tickets to test
    test_tickets = [
        {
            "ticket_id": f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}-001",
            "customer_email": "user@example.com",
            "subject": "Cannot login after password reset",
            "content": "I tried to reset my password but now I can't login. "
                       "Error message says 'Invalid credentials'.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        {
            "ticket_id": f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}-002",
            "customer_email": "admin@company.com",
            "subject": "URGENT: Production database down",
            "content": "Our production database is completely down. All customer "
                       "transactions are failing. This is a critical emergency!",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        {
            "ticket_id": f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}-003",
            "customer_email": "billing@client.com",
            "subject": "Invoice question",
            "content": "I received my invoice but the amount seems incorrect. "
                       "Can you help me understand the charges?",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    print(f"📤 Sending {len(test_tickets)} test tickets to SQS...\n")
    
    for ticket in test_tickets:
        print(f"Ticket: {ticket['subject']}")
        send_ticket_to_sqs(queue_url, ticket)
        print()
    
    print("✅ All test tickets sent!")
    print("\n📊 Monitor processing:")
    print("  - CloudWatch Logs: /aws/lambda/<function-name>")
    print("  - Check SNS for critical alerts (ticket #2)")


if __name__ == '__main__':
    main()