"""Tests for the Clockwork MCP server."""
from __future__ import annotations
import json
from pathlib import Path
import pytest
from clockwork.mcp_server import ClockworkMCPServer


@pytest.fixture
def server(tmp_path):
    cw = tmp_path / ".clockwork"
    cw.mkdir()
    (cw / "context.yaml").write_text(
        "project_name: test\nsummary: A test project\n", encoding="utf-8"
    )
    return ClockworkMCPServer(tmp_path)


def test_tools_list_has_six_tools(server):
    resp = server._handle({"method": "tools/list", "id": 1, "params": {}})
    tools = resp["result"]["tools"]
    assert len(tools) == 8
    names = {t["name"] for t in tools}
    assert "get_project_context" in names
    assert "query_graph" in names
    assert "check_file_safety" in names
    assert "git_pull" in names
    assert "git_push" in names


def test_get_project_context(server):
    result = server._call_tool("get_project_context", {})
    assert "project_name" in result
    assert result["project_name"] == "test"


def test_check_file_safety_normal(server):
    result = server._call_tool("check_file_safety",
                               {"file_path": "src/main.py", "operation": "modify"})
    assert isinstance(result["safe"], bool)


def test_initialize(server):
    resp = server._handle({
        "method": "initialize", "id": 1,
        "params": {"protocolVersion": "2024-11-05"}
    })
    assert resp["result"]["serverInfo"]["name"] == "clockwork"
