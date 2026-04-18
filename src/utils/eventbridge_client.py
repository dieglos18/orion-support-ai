"""
EventBridge client for emitting critical ticket alerts.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class EventBridgeClient:
    """
    Wrapper for Amazon EventBridge to emit custom events.
    """
    
    def __init__(self, event_bus_name: str = "default"):
        self.client = boto3.client('events')
        self.event_bus_name = event_bus_name
        logger.info(f"Initialized EventBridge client for bus: {event_bus_name}")
    
    def emit_critical_ticket_alert(
        self,
        ticket_id: str,
        category: str,
        urgency: int,
        customer_email: str,
        analysis_summary: str
    ) -> bool:
        """
        Emit a critical ticket alert to EventBridge.
        
        This triggers the EventBridge rule configured in Terraform,
        which sends notifications via SNS.
        
        Args:
            ticket_id: Unique ticket identifier
            category: Ticket category (Technical, Billing, etc.)
            urgency: Urgency level (4 or 5 for critical)
            customer_email: Customer's email
            analysis_summary: Brief summary from AI
        
        Returns:
            True if event was successfully emitted
        """
        try:
            event_detail = {
                "ticket_id": ticket_id,
                "category": category,
                "urgency": urgency,
                "customer_email": customer_email,
                "analysis_summary": analysis_summary,
                "timestamp": datetime.utcnow().isoformat(),
                "alert_type": "CRITICAL_TICKET"
            }
            
            # Put event to EventBridge
            response = self.client.put_events(
                Entries=[
                    {
                        'Time': datetime.utcnow(),
                        'Source': 'custom.support',
                        'DetailType': 'Critical Ticket Alert',
                        'Detail': json.dumps(event_detail),
                        'EventBusName': self.event_bus_name
                    }
                ]
            )
            
            # Check for failures
            if response['FailedEntryCount'] > 0:
                logger.error(f"Failed to emit event: {response['Entries']}")
                return False
            
            logger.info(f"Critical alert emitted for ticket {ticket_id}")
            return True
            
        except ClientError as e:
            logger.error(f"EventBridge error: {e}")
            return False