"""
LLM brain: OpenAI GPT-4o-mini + MCP tool calling + conversation memory.

Flow:
  1. Start MCP server processes (2GIS, Chocolife, ABR Group)
  2. Connect via stdio, collect available tools
  3. Run LLM with OpenAI function calling
  4. Execute tool calls through MCP clients OR local skill functions
  5. Return final text response + list of tool calls made
"""
import asyncio
import base64
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from config import (
    OPENAI_API_KEY,
    LLM_MODEL,
    MCP_SERVERS,
    MAX_RESPONSE_CHARS,
    IMAGE_DETAIL,
)
from agent.tools import TOOL_SCHEMAS, analyze_restaurant_photo

_openai = AsyncOpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """Ты — ИИ-аватар, персональный ассистент-проводник по ресторанам Алматы.

Правила:
- Отвечай всегда на русском языке
- Используй инструменты (MCP tools) для поиска реальных данных — НИКОГДА не выдумывай рестораны
- Если пользователь прислал фото ресторана И в сообщении УЖЕ есть блок [Оценка ресторана по фото] — используй эти данные напрямую, НЕ вызывай analyze_restaurant_photo повторно
- Если пользователь прислал фото ресторана БЕЗ блока оценки — вызови analyze_restaurant_photo
- Когда есть результат оценки ресторана, обязательно укажи: уровень заведения, атмосферу, для кого подходит
- Если спрашивают о скидках/акциях — используй search_deals (Chocolife)
- Если спрашивают о конкретном ресторане (Del Papa, Бочка, Pinta, Chagala) — используй get_restaurant_info
- Давай конкретные рекомендации: уровень заведения, атмосфера, для кого подходит, стоит ли идти
- Отвечай лаконично: максимум 3–4 предложения (ответ будет озвучен голосом)
- Никогда не пиши "Продолжение следует...", "To be continued" или любые обрывающие фразы
- Помни историю разговора в рамках сессии
"""


class MCPAgentSession:
    """
    Manages MCP server subprocesses and runs the LLM agent loop.
    Usage:
        async with MCPAgentSession() as session:
            response = await session.chat(messages, image_url=None)
    """

    def __init__(self) -> None:
        self._mcp_clients: dict[str, ClientSession] = {}
        self._mcp_tools: dict[str, Any] = {}   # name → mcp tool metadata
        self._mcp_server_for_tool: dict[str, str] = {}  # tool_name → server_name
        self._exit_stacks: list[Any] = []

    async def __aenter__(self) -> "MCPAgentSession":
        await self._start_mcp_servers()
        return self

    async def __aexit__(self, *_: Any) -> None:
        for stack in reversed(self._exit_stacks):
            try:
                await stack.__aexit__(None, None, None)
            except Exception:
                pass

    async def _start_mcp_servers(self) -> None:
        """Start all configured MCP servers and collect their tools."""
        project_root = Path(__file__).parent.parent

        for server_name, cfg in MCP_SERVERS.items():
            try:
                params = StdioServerParameters(
                    command=cfg["command"],
                    args=[str(project_root / cfg["args"][0])],
                    env={**os.environ},
                )
                cm = stdio_client(params)
                read, write = await cm.__aenter__()
                self._exit_stacks.append(cm)

                session_cm = ClientSession(read, write)
                session = await session_cm.__aenter__()
                self._exit_stacks.append(session_cm)

                await session.initialize()
                tools_result = await session.list_tools()

                self._mcp_clients[server_name] = session
                for tool in tools_result.tools:
                    self._mcp_tools[tool.name] = tool
                    self._mcp_server_for_tool[tool.name] = server_name

            except Exception as e:
                # Non-fatal: agent still works with other servers
                print(f"[MCP] Warning: could not start '{server_name}': {e}", flush=True)

    async def _call_mcp_tool(self, tool_name: str, arguments: dict) -> str:
        """Execute a tool via MCP client and return result as JSON string."""
        server_name = self._mcp_server_for_tool.get(tool_name)
        if not server_name or server_name not in self._mcp_clients:
            return json.dumps({"error": f"Tool '{tool_name}' not available"})

        try:
            result = await self._mcp_clients[server_name].call_tool(tool_name, arguments)
            # result.content is a list of TextContent/ImageContent
            texts = [c.text for c in result.content if hasattr(c, "text")]
            return texts[0] if texts else json.dumps({"result": "no content"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Route tool call to MCP or local skill."""
        if tool_name == "analyze_restaurant_photo":
            try:
                result = await analyze_restaurant_photo(arguments["image_url"])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": str(e)})

        return await self._call_mcp_tool(tool_name, arguments)

    def _build_messages(
        self,
        history: list[dict],
        user_text: str,
        image_url: str | None,
    ) -> list[ChatCompletionMessageParam]:
        """Build the full message list for the LLM call."""
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        # Conversation history (already formatted)
        for msg in history:
            messages.append(msg)  # type: ignore[arg-type]

        # Current user message
        if image_url:
            content: list[Any] = [
                {
                    "type": "image_url",
                    "image_url": {"url": image_url, "detail": IMAGE_DETAIL},
                },
                {"type": "text", "text": user_text or "Что на фото?"},
            ]
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": user_text})

        return messages

    async def chat(
        self,
        history: list[dict],
        user_text: str,
        image_url: str | None = None,
    ) -> tuple[str, list[str]]:
        """
        Run one agent turn.

        Returns:
            (assistant_text, tool_calls_log) where tool_calls_log is
            a list of human-readable strings describing what was called.
        """
        messages = self._build_messages(history, user_text, image_url)
        tool_calls_log: list[str] = []

        # Agentic loop: keep calling LLM until no more tool calls
        for _iteration in range(8):  # max 8 tool calls per turn
            response = await _openai.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,  # type: ignore[arg-type]
                tools=TOOL_SCHEMAS,  # type: ignore[arg-type]
                tool_choice="auto",
                temperature=0.5,
                max_tokens=600,
            )

            choice = response.choices[0]
            msg = choice.message

            # Append assistant message (may contain tool_calls)
            messages.append(msg)  # type: ignore[arg-type]

            if choice.finish_reason == "tool_calls" and msg.tool_calls:
                # Execute all tool calls in parallel
                tasks = []
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    tasks.append(self._execute_tool(tc.function.name, args))
                    tool_calls_log.append(
                        f"{tc.function.name}({tc.function.arguments[:80]})"
                    )

                results = await asyncio.gather(*tasks)

                # Append tool results
                for tc, result in zip(msg.tool_calls, results):
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

            else:
                # Final text response
                text = (msg.content or "").strip()
                # Remove continuation markers added by LLM
                for marker in ["Продолжение следует...", "Продолжение следует", "To be continued..."]:
                    text = text.replace(marker, "").strip()
                # Trim to MAX_RESPONSE_CHARS for TTS cost
                if len(text) > MAX_RESPONSE_CHARS:
                    text = text[:MAX_RESPONSE_CHARS].rsplit(".", 1)[0] + "."
                return text, tool_calls_log

        # Fallback if loop exhausted
        return "Извините, не удалось получить ответ. Попробуйте ещё раз.", tool_calls_log
