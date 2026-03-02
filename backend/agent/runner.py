"""
Step 3: Agent runner — LLM + tools + conversation memory.

Concepts:
- System prompt: tells the LLM its role and the current customer_id (so it can pass it to tools).
- Tools: we wrap the raw tools so the LLM only sees order_id/question; customer_id is injected from the session.
- Message history: we keep a list of HumanMessage, AIMessage, ToolMessage per session_id so the agent has context.
- Tool-calling loop: invoke model -> if response has tool_calls, run each tool, append ToolMessage(s), invoke again -> until we get a final text reply.
"""

from typing import Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from tools.order_tools import get_order_status, get_tracking_info, reorder_last_order, get_faq


# Default customer for demo (no auth yet). In production you'd get this from the session/token.
DEFAULT_CUSTOMER_ID = "cust-alice"

# In-memory store: session_id -> list of messages. In production use Redis or a DB.
_sessions: dict[str, list[BaseMessage]] = {}


def _make_tools(customer_id: str) -> list:
    """Build tools that inject customer_id so the LLM only passes order_id or question."""

    def get_status(order_id: Optional[str] = None) -> str:
        return get_order_status(customer_id, order_id)

    def get_tracking(order_id: Optional[str] = None) -> str:
        return get_tracking_info(customer_id, order_id)

    def reorder() -> str:
        return reorder_last_order(customer_id)

    return [
        StructuredTool.from_function(
            func=get_status,
            name="get_order_status",
            description="Get the status of the customer's order. Optionally pass order_id (e.g. QB-1001). If not provided, returns the most recent order.",
        ),
        StructuredTool.from_function(
            func=get_tracking,
            name="get_tracking_info",
            description="Get tracking details (driver, ETA) for the customer's order. Optionally pass order_id.",
        ),
        StructuredTool.from_function(
            func=reorder,
            name="reorder_last_order",
            description="Place a new order with the same items as the customer's most recent order.",
        ),
        StructuredTool.from_function(
            func=get_faq,
            name="get_faq",
            description="Answer FAQs about refunds, cancellation, delivery times, contact/support.",
        ),
    ]


def _system_prompt(customer_id: str) -> str:
    return f"""You are a helpful voice assistant for QuickBite, a food delivery app like DoorDash or Amazon delivery.

- Be concise and natural; your replies will be read aloud (TTS).
- Do not use markdown, bullet lists, or emojis.
- The current customer ID is: {customer_id}. Use the tools to look up orders, tracking, or reorder when the user asks.
- If the user just says hi or thanks, respond briefly without calling tools.
- If you don't have a tool for something, say so and suggest they contact support or ask about their order."""


def get_messages(session_id: str) -> list[BaseMessage]:
    """Return the message history for this session (copy so caller can append)."""
    return list(_sessions.get(session_id, []))


def append_messages(session_id: str, new_messages: list[BaseMessage]) -> None:
    """Append messages to the session history."""
    if session_id not in _sessions:
        _sessions[session_id] = []
    _sessions[session_id].extend(new_messages)


def chat(
    session_id: str,
    user_message: str,
    customer_id: Optional[str] = None,
) -> str:
    """
    Run the agent: add user message, run LLM with tools and history, return final text reply.
    """
    cid = customer_id or DEFAULT_CUSTOMER_ID
    tools = _make_tools(cid)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(tools)

    # Build message list: system + history + new user message
    system = SystemMessage(content=_system_prompt(cid))
    history = get_messages(session_id)
    new_human = HumanMessage(content=user_message)
    append_messages(session_id, [new_human])

    messages: list[BaseMessage] = [system] + history + [new_human]

    # Tool-calling loop: invoke until we get a response with no tool_calls
    while True:
        response = llm.invoke(messages)
        if not response.tool_calls:
            # Final reply
            reply = response.content if isinstance(response.content, str) else ""
            append_messages(session_id, [response])
            return reply

        # Run each tool call and collect ToolMessages
        tool_messages = []
        for tc in response.tool_calls:
            name = tc["name"]
            args = tc.get("args") or {}
            tool = next((t for t in tools if t.name == name), None)
            if not tool:
                tool_messages.append(
                    ToolMessage(content=f"Unknown tool: {name}", tool_call_id=tc["id"])
                )
                continue
            try:
                result = tool.invoke(args)
                tool_messages.append(
                    ToolMessage(content=str(result), tool_call_id=tc["id"])
                )
            except Exception as e:
                tool_messages.append(
                    ToolMessage(content=f"Error: {e}", tool_call_id=tc["id"])
                )

        messages.append(response)
        messages.extend(tool_messages)

    # unreachable
    return ""
