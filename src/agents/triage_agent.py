"""
Triage Agent: Classifies tickets into categories and urgency levels.
"""
import json
import logging
from typing import Dict, Any
from utils.bedrock_client import BedrockClient
from agents.prompts import TRIAGE_AGENT_PROMPT
from schemas.ticket import SupportTicket

logger = logging.getLogger(__name__)


class TriageAgent:
    """
    Agent responsible for ticket classification.

    Uses Chain-of-Thought reasoning to improve accuracy.
    """

    def __init__(self, bedrock_client: BedrockClient):
        self.bedrock = bedrock_client

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify the ticket.

        Args:
            state: Current graph state with 'ticket' field

        Returns:
            Updated state with 'triage_result' field
        """
        ticket: SupportTicket = state['ticket']

        logger.info(f"Triaging ticket: {ticket.ticket_id}")

        # Build user message with ticket details
        user_message = f"""
Ticket ID: {ticket.ticket_id}
Subject: {ticket.subject}
Content: {ticket.content}
Customer: {ticket.customer_email}
"""

        # Invoke Bedrock
        response = self.bedrock.invoke(
            system_prompt=TRIAGE_AGENT_PROMPT,
            user_message=user_message,
            max_tokens=500,
            temperature=0.2  # Low temp for consistent classification
        )

        # Parse JSON response
        try:
            triage_result = json.loads(response['content'])

            # Validate required fields
            required_fields = ['category', 'urgency', 'reasoning']
            if not all(field in triage_result for field in required_fields):
                raise ValueError(f"Missing required fields: {required_fields}")

            logger.info(
                f"Triage complete: {triage_result['category']} "
                f"(urgency {triage_result['urgency']})"
            )

            # Update state
            state['triage_result'] = triage_result
            state['usage_stats'] = {
                'triage_tokens': response['usage']
            }

            return state

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from Bedrock: {response['content']}")
            raise ValueError(f"Bedrock returned invalid JSON: {e}")
