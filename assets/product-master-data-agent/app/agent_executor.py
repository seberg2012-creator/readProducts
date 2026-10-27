import json
import logging
from typing import Any

from langchain_core.messages import SystemMessage
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.tools import BaseTool, StructuredTool

from a2a.server.agent_execution import AgentExecutor as A2AAgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from agent import SampleAgent
from datetime_tool import get_datetime_tool
from load_skill_resources import get_load_skill_resource_tool
from mcp_providers.agw import get_mcp_tools
from prompt_injection_detector import wrap_tool

logger = logging.getLogger(__name__)

# Maximum characters allowed in a single tool response before truncation.
# ~6 000 chars ≈ ~2 000 tokens — safely within a 12 000-token summarisation window.
_MAX_TOOL_OUTPUT_CHARS = 6_000


def _truncate_tool_output(raw: Any) -> str:
    """Serialise a tool result and hard-cap it to avoid context overflow.

    If the serialised output exceeds _MAX_TOOL_OUTPUT_CHARS, the excess is
    dropped and a notice is appended so the LLM knows the response was cut.
    """
    if isinstance(raw, str):
        text = raw
    else:
        try:
            text = json.dumps(raw, ensure_ascii=False)
        except Exception:
            text = str(raw)

    if len(text) <= _MAX_TOOL_OUTPUT_CHARS:
        return text

    truncated = text[:_MAX_TOOL_OUTPUT_CHARS]
    notice = (
        f"\n\n[TRUNCATED — response exceeded {_MAX_TOOL_OUTPUT_CHARS} characters. "
        "Use $select and $top to retrieve fewer fields / records.]"
    )
    logger.warning(
        "Tool response truncated from %d to %d characters.", len(text), _MAX_TOOL_OUTPUT_CHARS
    )
    return truncated + notice


def _make_truncating_wrapper(inner: BaseTool) -> BaseTool:
    """Return a StructuredTool that proxies *inner* and caps its output size."""
    def _run_fn(*args: Any, **kwargs: Any) -> str:
        return _truncate_tool_output(inner._run(*args, **kwargs))

    async def _arun_fn(*args: Any, **kwargs: Any) -> str:
        return _truncate_tool_output(await inner._arun(*args, **kwargs))

    return StructuredTool(
        name=inner.name,
        description=inner.description,
        args_schema=inner.args_schema,
        func=_run_fn,
        coroutine=_arun_fn,
    )


class AgentExecutor(A2AAgentExecutor):
    def __init__(self):
        self.agent = SampleAgent()
        self.skill_tools = [get_datetime_tool(), *get_load_skill_resource_tool()]

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent and stream results back via A2A protocol.

        Discovers and loads MCP tools from Agent Gateway before each execution.
        The user token is read from the context var set by JWTContextMiddleware.

        Args:
            context: Request context containing user input and task info
            event_queue: Queue for publishing task status updates

        Raises:
            ServerError: On unrecoverable agent execution errors
        """
        query = context.get_user_input()
        task = context.current_task
        if not task:
            assert context.message is not None, "Cannot create task without a message"
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        # Load MCP tools — user token is read from context var set by JWTContextMiddleware
        tools = []
        try:
            tools = await get_mcp_tools()
            if not tools:
                logger.warning("No tools returned from Agent Gateway")
        except Exception as e:
            logger.error(f"Failed to load tools from Agent Gateway: {e}")

        tools = [*tools, *self.skill_tools]

        # Wrap all tools: first truncate oversized OData responses, then scan for injection
        tools = [_make_truncating_wrapper(wrap_tool(t)) for t in tools]

        from agent import get_system_prompt
        _system_prompt = get_system_prompt()
        _msg_tokens = count_tokens_approximately([SystemMessage(content=_system_prompt)])
        _total_tokens = count_tokens_approximately([SystemMessage(content=_system_prompt)], tools=list(tools))
        logger.info(
            "Loaded %d tool(s); token estimate — prompt: %d, tools: %d, total: %d",
            len(tools), _msg_tokens, _total_tokens - _msg_tokens, _total_tokens,
        )

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        try:
            async for item in self.agent.stream(query, task.context_id, tools=tools):
                is_task_complete = item["is_task_complete"]
                require_user_input = item["require_user_input"]
                content = item["content"]

                if require_user_input:
                    # Agent requests more input
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(content, task.context_id, task.id),
                        final=True,
                    )
                    break
                elif is_task_complete:
                    # Completed: add artifact and complete task
                    await updater.add_artifact(
                        [Part(root=TextPart(text=content))], name="agent_result"
                    )
                    await updater.complete()
                    break
                else:
                    # Working status update
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(content, task.context_id, task.id),
                    )
        except Exception as e:
            logger.exception("Agent execution error")
            raise ServerError(error=InternalError()) from e

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise ServerError(error=UnsupportedOperationError())
