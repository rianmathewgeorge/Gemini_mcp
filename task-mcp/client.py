import os
import asyncio
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai
from google.genai import types
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("client")

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"

# How to launch the server: run "python server.py"
server_params = StdioServerParameters(command="python", args=["server.py"])


def build_gemini_tools(mcp_tools):
    """Convert the MCP server's tool list into Gemini function declarations."""
    declarations = [
        types.FunctionDeclaration(
            name=t.name,
            description=t.description or "",
            parameters_json_schema=t.inputSchema,
        )
        for t in mcp_tools
    ]
    return [types.Tool(function_declarations=declarations)]


async def ask(gemini, session, gemini_tools, prompt):
    """Send one prompt, run any tools Gemini asks for, return the final text answer."""
    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    config = types.GenerateContentConfig(
        tools=gemini_tools,
        temperature=0,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    for _ in range(5):  # safety cap on tool-call rounds
        response = await gemini.aio.models.generate_content(
            model=MODEL, contents=contents, config=config
        )

        calls = response.function_calls
        if not calls:
            return response.text

        # Record Gemini's request, then run each tool against the MCP server
        contents.append(response.candidates[0].content)
        tool_parts = []
        for call in calls:
            logger.info("Gemini requested tool: %s(%s)", call.name, dict(call.args))
            result = await session.call_tool(call.name, dict(call.args))
            result_text = result.content[0].text if result.content else ""
            tool_parts.append(
                types.Part.from_function_response(
                    name=call.name, response={"result": result_text}
                )
            )
        contents.append(types.Content(role="user", parts=tool_parts))

    return response.text


async def main():
    if not API_KEY:
        print("ERROR: GEMINI_API_KEY not found. Create a .env file with GEMINI_API_KEY=your_key")
        return

    gemini = genai.Client(api_key=API_KEY)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tool_list = await session.list_tools()
            gemini_tools = build_gemini_tools(tool_list.tools)
            logger.info("Connected. %d tools available to Gemini.", len(tool_list.tools))

            print("\nTask assistant ready. Ask me about your tasks. Type 'quit' to exit.\n")
            while True:
                prompt = input("You: ").strip()
                if prompt.lower() in {"quit", "exit"}:
                    break
                if not prompt:
                    continue
                answer = await ask(gemini, session, gemini_tools, prompt)
                print(f"\nAssistant: {answer}\n")


if __name__ == "__main__":
    asyncio.run(main())
