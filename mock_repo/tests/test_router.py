"""Unit tests for the router agent. These pass today because they
mock the LLM client and never actually execute .format() against a
real ticket payload."""

from prompts import CUSTOMER_ROUTER_PROMPT


def test_router_prompt_is_defined():
    assert "CUSTOMER_ROUTER_PROMPT" in dir()
    assert CUSTOMER_ROUTER_PROMPT is not None
