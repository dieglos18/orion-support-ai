"""
LangGraph workflow definition: Multi-agent ticket processing.

Graph structure:
    START -> Triage -> Response -> Validation -> Decision -> END
                                                    |
                                                    v
                                            (EventBridge if critical)
"""
import logging
from typing import Any, Dict, Literal, TypedDict, cast
from langgraph.graph import StateGraph, END
from schemas.ticket import SupportTicket, AIAnalysis
from utils.bedrock_client import BedrockClient
from agents.triage_agent import TriageAgent
from agents.response_agent import ResponseAgent
from agents.validation_agent import ValidationAgent

logger = logging.getLogger(__name__)


class SupportTicketState(TypedDict, total=False):
    """
    State passed between agents in the graph.

    LangGraph 0.2+ builds state channels from this schema. Subclassing Dict[str, Any]
    alone registers no channels and triggers InvalidUpdateError ("Must write to at
    least one of []").
    """

    ticket: Any  # SupportTicket at runtime
    triage_result: Dict[str, Any]
    draft_response: Dict[str, Any]
    validation_result: Dict[str, Any]
    final_approved: bool
    usage_stats: Dict[str, Any]
    final_analysis: Dict[str, Any]
    total_cost: float
    error: str


def create_support_workflow() -> Any:
    """
    Build the LangGraph workflow.

    Returns:
        Compiled graph (StateGraph.compile()) with invoke().
    """
    # Initialize Bedrock client (shared across agents)
    bedrock = BedrockClient()

    # Initialize agents
    triage_agent = TriageAgent(bedrock)
    response_agent = ResponseAgent(bedrock)
    validation_agent = ValidationAgent(bedrock)

    # Define workflow
    workflow = StateGraph(SupportTicketState)

    # Add nodes
    workflow.add_node("triage", triage_agent.process)
    workflow.add_node("response", response_agent.process)
    workflow.add_node("validation", validation_agent.process)

    # Define routing logic
    def route_after_validation(
        state: SupportTicketState
    ) -> Literal["retry_response", "finalize"]:
        """
        Decide next step after validation.

        If validation failed, could retry response generation.
        For MVP, we just proceed to finalize.
        """
        if state.get('final_approved', False):
            return "finalize"
        else:
            # In production, might retry with different prompt
            logger.warning("Validation failed but proceeding (no retry logic yet)")
            return "finalize"

    def finalize_result(state: SupportTicketState) -> SupportTicketState:
        """
        Final node: Package result into AIAnalysis schema.
        """
        triage = state['triage_result']
        draft = state['draft_response']

        # Build final analysis (Pydantic enforced)
        try:
            analysis = AIAnalysis(
                category=triage['category'],
                urgency=triage['urgency'],
                reasoning=triage['reasoning'],
                suggested_reply=draft['suggested_reply'],
                requires_human_review=draft.get('requires_human_review', False)
            )

            state['final_analysis'] = analysis.model_dump()

            # Calculate total cost
            usage = state.get('usage_stats', {})
            total_input = sum(
                u.get('input_tokens', 0)
                for u in usage.values() if isinstance(u, dict)
            )
            total_output = sum(
                u.get('output_tokens', 0)
                for u in usage.values() if isinstance(u, dict)
            )

            cost = bedrock.estimate_cost(total_input, total_output)
            state['total_cost'] = cost

            logger.info(
                f"Processing complete. "
                f"Tokens: {total_input} in, {total_output} out. "
                f"Cost: ${cost:.6f}"
            )

        except Exception as e:
            logger.error(f"Failed to create final analysis: {e}")
            state['error'] = str(e)

        return state

    workflow.add_node("finalize", finalize_result)

    # Define edges (flow control)
    workflow.set_entry_point("triage")
    workflow.add_edge("triage", "response")
    workflow.add_edge("response", "validation")
    workflow.add_conditional_edges(
        "validation",
        route_after_validation,
        {
            "retry_response": "response",  # Could loop back
            "finalize": "finalize"
        }
    )
    workflow.add_edge("finalize", END)

    # Compile
    app = workflow.compile()

    logger.info("LangGraph workflow compiled successfully")

    return app


def process_ticket(ticket_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point: Process a single ticket through the workflow.

    Args:
        ticket_data: Raw ticket data (dict)

    Returns:
        Final state with analysis result
    """
    # Validate input with Pydantic
    try:
        ticket = SupportTicket(**ticket_data)
    except Exception as e:
        logger.error(f"Invalid ticket data: {e}")
        raise ValueError(f"Ticket validation failed: {e}")

    initial_state: SupportTicketState = {"ticket": ticket}

    # Run workflow
    app = create_support_workflow()
    final_state = cast(Dict[str, Any], app.invoke(initial_state))

    return final_state
