import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_script = os.path.join(os.path.dirname(__file__), "server.py")
    
    # Configure MCP server parameters
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=dict(os.environ)
    )

    print("Connecting to QA-Test-Automation MCP Server...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 1. Initialize MCP handshake
            await session.initialize()
            print("Connected successfully!")

            # 2. List available tools exposed by our server
            tools_response = await session.list_tools()
            print("\nExposed MCP Tools:")
            for tool in tools_response.tools:
                print(f"  • {tool.name}: {tool.description.splitlines()[0]}")

            # 3. Call Tool: evaluate_rag_query
            print("\nExecuting Tool: evaluate_rag_query('What is the return policy?')...")
            rag_result = await session.call_tool(
                "evaluate_rag_query",
                arguments={"query": "What is the return policy?"}
            )
            print("Tool Output:")
            print(rag_result.content[0].text)

            # 4. Call Tool: run_tests (runs API test suite)
            print("\nExecuting Tool: run_tests('tests/api/test_sample_api.py')...")
            test_result = await session.call_tool(
                "run_tests",
                arguments={"target": "tests/api/test_sample_api.py"}
            )
            print("Tool Output:")
            print(test_result.content[0].text[:300] + "\n...[truncated]")

if __name__ == "__main__":
    asyncio.run(main())