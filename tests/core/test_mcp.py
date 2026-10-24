import json
import os
import subprocess
import sys


SERVER = os.path.join(os.path.dirname(__file__), "..", "..", "mcp", "server.py")
CORE_TOOLS = {"gm_read_project", "gm_validate_project", "gm_inspect_assets", "gm_read_script"}


def rpc(messages, core_only=False):
    """Sends newline-delimited JSON-RPC messages to a real server process and returns responses by id."""
    env = dict(os.environ)
    env.pop("GM_KIT_NO_EXTENSIONS", None)
    if core_only:
        env["GM_KIT_NO_EXTENSIONS"] = "1"
    payload = "\n".join(m if isinstance(m, str) else json.dumps(m) for m in messages) + "\n"
    res = subprocess.run([sys.executable, SERVER], input=payload.encode("utf-8"), capture_output=True, env=env, timeout=60)
    assert res.returncode == 0, res.stderr.decode()
    out = [json.loads(l) for l in res.stdout.decode("utf-8").splitlines() if l.strip()]
    return {r.get("id"): r for r in out}, out


def call(name, args, id_=1):
    return {"jsonrpc": "2.0", "id": id_, "method": "tools/call", "params": {"name": name, "arguments": args}}


def tool_json(resp):
    assert resp["result"]["isError"] is False, resp
    return json.loads(resp["result"]["content"][0]["text"])


def test_initialize_negotiates_version():
    by_id, _ = rpc([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
        {"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {"protocolVersion": "1999-01-01"}},
    ])
    assert by_id[1]["result"]["protocolVersion"] == "2025-03-26"
    assert by_id[2]["result"]["protocolVersion"] == "2025-06-18"
    assert by_id[1]["result"]["capabilities"] == {"tools": {"listChanged": False}}


def test_notifications_get_no_response():
    _, out = rpc([{"jsonrpc": "2.0", "method": "notifications/initialized"}, {"jsonrpc": "2.0", "id": 7, "method": "ping"}])
    assert [r["id"] for r in out] == [7]


def test_protocol_errors():
    by_id, out = rpc([
        "not json",
        {"jsonrpc": "2.0", "id": 1, "method": "nope"},
        call("gm_unknown", {}, 2),
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "gm_read_project", "arguments": [1]}},
    ])
    assert out[0]["error"]["code"] == -32700
    assert by_id[1]["error"]["code"] == -32601
    assert by_id[2]["error"]["code"] == -32602
    assert by_id[3]["error"]["code"] == -32602


def test_tool_errors_are_results_with_is_error(tmp_path):
    by_id, _ = rpc([call("gm_read_project", {}, 1), call("gm_read_project", {"project_path": str(tmp_path)}, 2)])
    for i in (1, 2):
        assert by_id[i]["result"]["isError"] is True
    assert "project_path" in by_id[1]["result"]["content"][0]["text"]


def test_without_extensions_lists_only_core_tools():
    by_id, _ = rpc([{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}], core_only=True)
    assert {t["name"] for t in by_id[1]["result"]["tools"]} == CORE_TOOLS


def test_core_tools_on_fixture(fixture_project):
    by_id, _ = rpc([
        call("gm_read_project", {"project_path": fixture_project}, 1),
        call("gm_validate_project", {"project_path": fixture_project}, 2),
        call("gm_read_script", {"project_path": fixture_project, "script_name": "scr_util"}, 3),
        call("gm_read_script", {"project_path": fixture_project, "script_name": "../../x"}, 4),
    ], core_only=True)
    assert tool_json(by_id[1])["categories"]["objects"] == ["obj_wall", "obj_player"]
    assert tool_json(by_id[2])["passed"] is True
    assert "function approach" in tool_json(by_id[3])["content"]
    assert by_id[4]["result"]["isError"] is True


def test_malformed_messages_do_not_kill_the_server():
    """Review regressions: each of these used to end the server process."""
    by_id, out = rpc([
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": [1]},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": "abc"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": ["x"]}},
        "[" * 100000,
        '{"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "gm_read_project", '
        '"arguments": {"project_path": NaN}}}',
        {"jsonrpc": "2.0", "id": 5, "method": "ping"},
    ], core_only=True)
    assert by_id[1]["error"]["code"] == -32602
    assert by_id[2]["error"]["code"] == -32602
    assert by_id[3]["error"]["code"] == -32602
    assert sum(1 for r in out if r.get("error", {}).get("code") == -32700) == 2
    assert by_id[5]["result"] == {}


def test_invalid_utf8_does_not_kill_the_server():
    payload = b'\xff\xfe garbage\n{"jsonrpc":"2.0","id":9,"method":"ping"}\n'
    res = subprocess.run([sys.executable, SERVER], input=payload, capture_output=True,
                         env={**os.environ, "GM_KIT_NO_EXTENSIONS": "1"}, timeout=60)
    lines = [json.loads(l) for l in res.stdout.decode().splitlines() if l.strip()]
    assert lines[0]["error"]["code"] == -32700 and lines[1]["id"] == 9
