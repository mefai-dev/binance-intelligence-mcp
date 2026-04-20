"""Binance Intelligence MCP Server ··· 12 computed intelligence tools for Binance."""

__version__ = "1.1.0"


def main():
    """Entry point for the binance-intelligence-mcp command."""
    from .server import mcp
    mcp.run()
