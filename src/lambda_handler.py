"""
AWS Lambda handler for the Orion AI Support Orchestrator.
Entry point for SQS-triggered ticket processing.
"""
import json
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler function.
    
    Args:
        event: SQS event with ticket data
        context: Lambda context object
    
    Returns:
        Response with processing status
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Extract SQS records
    records = event.get('Records', [])
    
    if not records:
        logger.warning("No SQS records found in event")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No records to process'})
        }
    
    processed_count = 0
    
    for record in records:
        try:
            # Parse message body
            message_body = json.loads(record['body'])
            logger.info(f"Processing ticket: {message_body}")
            
            # TODO: Phase 3 - Process with LangGraph
            # result = process_ticket_with_langgraph(message_body)
            
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}", exc_info=True)
            # Note: If we raise here, message goes back to queue
            # For now, we'll log and continue
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': processed_count,
            'total': len(records)
        })
    }