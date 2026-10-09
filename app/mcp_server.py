"""Official MCP v1 SDK, pinned below v2 for a stable client contract."""
from mcp.server.fastmcp import FastMCP
from .config import SPEC
from .service import DecisionRequest, decide, knowledge, metadata

mcp = FastMCP(SPEC['title'])

@mcp.tool()
def search_policy(query: str) -> dict:
    """Retrieve cited synthetic operating-policy excerpts without calling an LLM."""
    if not 3 <= len(query) <= 700:
        raise ValueError('query must contain 3 to 700 characters')
    return {'results': knowledge().search(query)}

@mcp.tool()
def analyze_operation(features: dict[str, float], question: str = 'Explain the operational recommendation.') -> dict:
    """Create an advisory decision and local audit record. Live mode can incur LLM cost."""
    return decide(DecisionRequest(features=features, question=question))

@mcp.tool()
def model_card() -> dict:
    """Return input schema and held-out synthetic evaluation metrics."""
    return metadata()

if __name__ == '__main__':
    mcp.run(transport='stdio')
