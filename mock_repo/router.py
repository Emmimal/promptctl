"""Agent entry point that routes an incoming support ticket."""

from prompts import CUSTOMER_ROUTER_PROMPT


def run_agent(user_ticket: str, user_domain: str) -> str:
    # Unchanged call site: still passes `ticket`, not `ticket_id`.
    formatted_prompt = CUSTOMER_ROUTER_PROMPT.format(
        ticket=user_ticket,
        domain=user_domain,
    )
    return formatted_prompt
