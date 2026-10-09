import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.config import ROOT, SPEC

def test_stdio_round_trip(tmp_path):
    async def exercise():
        params = StdioServerParameters(command=sys.executable,args=['-m','app.mcp_server'],cwd=str(ROOT),
                    env={**os.environ,'STATE_DIR':str(tmp_path),'LLM_PROVIDER':'demo'})
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listing = await session.list_tools()
                assert {tool.name for tool in listing.tools} == {'search_policy','analyze_operation','model_card'}
                result = await session.call_tool('search_policy', {'query': SPEC['retrieval_query']})
                assert not result.isError
                result = await session.call_tool('analyze_operation', {'features':SPEC['scenarios'][0]['features']})
                assert not result.isError
    asyncio.run(asyncio.wait_for(exercise(), timeout=45))
