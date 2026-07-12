import os, logging
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("client")

SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
CLIENT_ID = os.getenv("MCP_CLIENT_ID", "mcp-client")
CLIENT_SECRET = os.getenv("MCP_CLIENT_SECRET", "mcp-secret")
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"


async def get_token() -> str:
    """Authenticate to the server and return a JWT (step 1: must happen before any tool access)."""
    async with httpx.AsyncClient() as http:
        r = await http.post(f"{SERVER_URL}/token",
                            data={"username": CLIENT_ID, "password": CLIENT_SECRET})
        r.raise_for_status()
        logger.info("Authenticated with server; token acquired.")
        return r.json()["access_token"]


def build_gemini_tools(mcp_tools):
    decls = [types.FunctionDeclaration(name=t.name, description=t.description or "",
                                       parameters_json_schema=t.inputSchema) for t in mcp_tools]
    return [types.Tool(function_declarations=decls)]


async def run_query(prompt: str) -> str:
    token = await get_token()                       # 1. authenticate FIRST
    headers = {"Authorization": f"Bearer {token}"}  # 2. present token on every MCP call
    async with streamablehttp_client(f"{SERVER_URL}/mcp", headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()              # 3. MCP handshake (rejected if token invalid)
            tool_list = await session.list_tools()
            gemini_tools = build_gemini_tools(tool_list.tools)
            gemini = genai.Client(api_key=API_KEY)

            contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
            config = types.GenerateContentConfig(
                tools=gemini_tools, temperature=0,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
            for _ in range(5):
                resp = await gemini.aio.models.generate_content(model=MODEL, contents=contents, config=config)
                calls = resp.function_calls
                if not calls:
                    return resp.text
                contents.append(resp.candidates[0].content)
                parts = []
                for call in calls:
                    logger.info("Gemini requested tool: %s(%s)", call.name, dict(call.args))
                    result = await session.call_tool(call.name, dict(call.args))
                    txt = result.content[0].text if result.content else ""
                    parts.append(types.Part.from_function_response(name=call.name, response={"result": txt}))
                contents.append(types.Content(role="user", parts=parts))
            return resp.text


app = FastAPI(title="Task Assistant Client")

class ChatIn(BaseModel):
    message: str

@app.post("/chat")
async def chat(body: ChatIn):
    try:
        return {"answer": await run_query(body.message)}
    except Exception as e:
        logger.exception("chat failed")
        raise HTTPException(status_code=500, detail=str(e))
