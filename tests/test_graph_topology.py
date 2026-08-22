"""DEC-013 candidate (decide-then-retrieve reordering): structural
assertion on build_graph()'s compiled node/edge shape. Cheaper and more
durable than trying to force the no-tool branch through the full graph in
fake mode (fake mode always takes the tool-call branch by design -- see
tests/test_graph_shell.py -- so retrieve/generate are otherwise
unreachable in a fake-mode integration test).
"""

import os

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "mock")

from agent.graph import build_graph  # noqa: E402


def test_graph_has_the_expected_nodes():
    graph = build_graph().get_graph()
    assert set(graph.nodes.keys()) == {
        "__start__",
        "__end__",
        "decide",
        "retrieve",
        "generate",
        "tool_invoke",
        "human_approval",
        "fallback",
    }


def test_graph_topology_no_tool_path_reaches_retrieve_and_generate():
    graph = build_graph().get_graph()
    edges = {(e.source, e.target) for e in graph.edges}

    # decide is the sole entry point.
    assert ("__start__", "decide") in edges
    # decide's no-tool branch reaches retrieve, then generate -- the
    # redesign's whole point.
    assert ("decide", "retrieve") in edges
    assert ("retrieve", "generate") in edges
    # decide's tool-call branch is unchanged in shape from before the redesign.
    assert ("decide", "tool_invoke") in edges
    assert ("tool_invoke", "human_approval") in edges
    # every node that can fail routes to fallback, which is the only
    # unconditional edge into __end__.
    for node in ("decide", "retrieve", "generate", "tool_invoke", "human_approval"):
        assert (node, "fallback") in edges
    assert ("fallback", "__end__") in edges


def test_retrieve_is_no_longer_the_entry_point():
    graph = build_graph().get_graph()
    edges = {(e.source, e.target) for e in graph.edges}
    assert ("__start__", "retrieve") not in edges
