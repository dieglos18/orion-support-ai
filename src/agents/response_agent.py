"""
Response Agent: Generates customer-facing draft replies.
"""
import json
import logging
from typing import Dict, Any
from utils.bedrock_client import BedrockClient
from agents.prompts import RESPONSE_AGENT_PROMPT

logger = logging.getLogger(__name__)


class ResponseAgent:
    """
    Agent responsible for drafting customer responses.
    """
    
    def __init__(self, bedrock_client: BedrockClient):
        self.bedrock = bedrock_client
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate draft response.
        
        Args:
            state: Must contain 'ticket' and 'triage_result'
        
        Returns:
            Updated state with 'draft_response' field
        """
        ticket = state['ticket']
        triage = state['triage_result']
        
        logger.info(f"Generating response for ticket: {ticket.ticket_id}")
        
        # Format prompt with triage context
        system_prompt = RESPONSE_AGENT_PROMPT.format(
            category=triage['category'],
            urgency=triage['urgency'],
            ticket_content=ticket.content
        )
        
        user_message = f"""
Customer's issue: {ticket.subject}

Details: {ticket.content}

Generate a professional response that addresses their concern.
"""
        
        # Invoke Bedrock
        response = self.bedrock.invoke(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=1024,
            temperature=0.5  # Moderate creativity for natural language
        )
        
        # Parse response
        try:
            draft = json.loads(response['content'])
            
            logger.info(
                f"Response generated "
                f"(requires_review: {draft.get('requires_human_review', False)})"
            )
            
            # Update state
            state['draft_response'] = draft
            
            # Accumulate token usage
            if 'usage_stats' not in state:
                state['usage_stats'] = {}
            state['usage_stats']['response_tokens'] = response['usage']
            
            return state
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from Bedrock: {response['content']}")
            raise ValueError(f"Response agent failed to produce valid JSON: {e}")