"""
AWS Lambda handler for the AI Support Orchestrator.
Entry point for SQS-triggered ticket processing.
"""
import json
import logging
import os
from typing import Dict, Any
from agents.workflow import process_ticket
from utils.eventbridge_client import EventBridgeClient

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
logger = logging.getLogger()
logger.setLevel(log_level)

# Initialize EventBridge client
eventbridge = EventBridgeClient()


def emit_critical_alert_if_needed(ticket_data: Dict[str, Any], analysis: Dict[str, Any]):
    """
    Emit EventBridge event if ticket is critical (urgency >= 4).
    
    Args:
        ticket_data: Original ticket data
        analysis: AI analysis result
    """
    urgency = analysis.get('urgency', 0)
    
    if urgency >= 4:
        logger.info(f"Emitting critical alert for urgency {urgency}")
        
        success = eventbridge.emit_critical_ticket_alert(
            ticket_id=ticket_data.get('ticket_id', 'unknown'),
            category=analysis.get('category', 'Unknown'),
            urgency=urgency,
            customer_email=ticket_data.get('customer_email', ''),
            analysis_summary=analysis.get('reasoning', 'No summary available')
        )
        
        if success:
            logger.info("Critical alert sent to EventBridge → SNS")
        else:
            logger.error("Failed to send critical alert")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler function.
    
    Flow:
    1. Parse SQS message
    2. Run ticket through LangGraph workflow
    3. Emit EventBridge event if urgency >= 4
    4. Return result
    
    Args:
        event: SQS event with ticket data
        context: Lambda context object
    
    Returns:
        Response with processing status
    """
    logger.info(f"Received {len(event.get('Records', []))} SQS messages")
    
    records = event.get('Records', [])
    
    if not records:
        logger.warning("No SQS records found in event")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No records to process'})
        }
    
    processed_results = []
    
    for record in records:
        try:
            # Parse message body
            message_body = json.loads(record['body'])
            logger.info(f"Processing ticket: {message_body.get('ticket_id')}")
            
            # Run through LangGraph workflow
            result = process_ticket(message_body)
            
            # Check if processing succeeded
            if 'error' in result:
                logger.error(f"Workflow error: {result['error']}")
                processed_results.append({
                    'ticket_id': message_body.get('ticket_id'),
                    'status': 'failed',
                    'error': result['error']
                })
                continue
            
            # Extract final analysis
            analysis = result.get('final_analysis', {})
            
            # Log result
            logger.info(
                f"Ticket {message_body.get('ticket_id')} processed: "
                f"{analysis.get('category')} (urgency {analysis.get('urgency')})"
            )
            
            # Emit critical alert if needed
            emit_critical_alert_if_needed(message_body, analysis)
            
            processed_results.append({
                'ticket_id': message_body.get('ticket_id'),
                'status': 'success',
                'analysis': analysis,
                'cost': result.get('total_cost', 0),
                'critical_alert_sent': analysis.get('urgency', 0) >= 4
            })
            
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}", exc_info=True)
            processed_results.append({
                'ticket_id': 'unknown',
                'status': 'failed',
                'error': str(e)
            })
    
    # Return summary
    success_count = sum(1 for r in processed_results if r['status'] == 'success')
    
    return {
        'statusCode': 200 if success_count > 0 else 500,
        'body': json.dumps({
            'processed': success_count,
            'failed': len(processed_results) - success_count,
            'results': processed_results
        }, indent=2)
    }