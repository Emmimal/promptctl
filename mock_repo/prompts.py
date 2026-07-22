"""Prompt templates for the support routing agent.

Convention: any top-level string constant ending in _PROMPT is treated
as a registered prompt symbol. Its symbol_id is derived by lowercasing
the constant name and dropping the trailing _PROMPT suffix.
"""

# NOTE: {ticket} was renamed to {ticket_id} to match the new database
# schema. This is the breaking change promptctl is meant to catch.
CUSTOMER_ROUTER_PROMPT = "Categorize support request for {ticket_id} in domain {domain}."
