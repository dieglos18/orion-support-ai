"""
Validation Agent: Quality control for AI-generated responses.
"""
import json
import logging
from typing import Dict, Any
from utils.bedrock_client import BedrockClient
from agents.prompts import VALIDATION_AGENT_PROMPT

logger = logging.getLogger(__name__)


class ValidationAgent:
    """
    Agent responsible for validating response quality.
    """

    def __init__(self, bedrock_client: BedrockClient):
        self.bedrock = bedrock_client

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the draft response.

        Args:
            state: Must contain 'draft_response'

        Returns:
            Updated state with 'validation_result' field
        """
        draft = state['draft_response']

        logger.info("Validating draft response")

        # Format prompt with draft to validate
        system_prompt = VALIDATION_AGENT_PROMPT.format(
            response_to_validate=json.dumps(draft, indent=2)
        )

        user_message = "Validate the response above."

        # Invoke Bedrock
        response = self.bedrock.invoke(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=512,
            temperature=0.1  # Very low temp for consistent validation
        )

        # Parse validation result
        try:
            validation = json.loads(response['content'])

            passed = validation.get('passed', False)
            score = validation.get('validation_score', 0)

            logger.info(
                f"Validation complete: "
                f"{'PASSED' if passed else 'FAILED'} (score: {score}/10)"
            )

            # Update state
            state['validation_result'] = validation
            state['final_approved'] = passed

            # Accumulate tokens
            if 'usage_stats' not in state:
                state['usage_stats'] = {}
            state['usage_stats']['validation_tokens'] = response['usage']

            return state

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from Bedrock: {response['content']}")
            raise ValueError(f"Validation agent failed: {e}")
