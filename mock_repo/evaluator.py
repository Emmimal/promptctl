"""Offline evaluation harness that replays historical tickets through
the same router prompt to score routing accuracy."""

from prompts import CUSTOMER_ROUTER_PROMPT


def score_routing(historical_ticket: str, historical_domain: str) -> str:
    formatted_prompt = CUSTOMER_ROUTER_PROMPT.format(
        ticket=historical_ticket,
        domain=historical_domain,
    )
    return formatted_prompt
