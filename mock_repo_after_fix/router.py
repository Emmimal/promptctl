"""Agent entry point that routes an incoming support ticket."""

from prompts import CUSTOMER_ROUTER_PROMPT


def run_agent(user_ticket: str, user_domain: str) -> str:
    # Fixed: caller updated to match the renamed {ticket_id} variable.
    formatted_prompt = CUSTOMER_ROUTER_PROMPT.format(
        ticket_id=user_ticket,
        domain=user_domain,
    )
    return formatted_prompt
