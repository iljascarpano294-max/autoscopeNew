"""Stage 15 task 2: A2A across two real processes on the loopback."""

import asyncio
import json
import socket
import subprocess
import sys
from pathlib import Path

from agentscope.agent import A2AAgent
from agentscope.message import TextBlock, UserMsg

SERVER = Path(__file__).resolve().parent.parent / "examples" / "a2a_server.py"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_a2a_e2e() -> None:
    port = _free_port()
    process = subprocess.Popen(
        [
            sys.executable,
            str(SERVER),
            "--port",
            str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    async def wait_ready():
        import httpx

        for _ in range(60):
            try:
                response = await httpx.AsyncClient().get(
                    f"http://127.0.0.1:{port}/health",
                )
                if response.status_code == 200:
                    return True
            except httpx.HTTPError:
                await asyncio.sleep(0.25)
        return False

    try:
        assert asyncio.run(wait_ready()), "server did not become ready"

        async def call():
            agent = A2AAgent(endpoint=f"http://127.0.0.1:{port}/a2a", timeout=10)
            final = None
            async for item in agent.reply_stream(UserMsg("Alice", "ping")):
                if item.__class__.__name__ == "Msg":
                    final = item
            return final

        final = asyncio.run(call())
        assert final is not None
        assert "pong" in final.get_text_content()
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    # The server process was reclaimed.
    assert process.poll() is not None
    if process.stdout:
        process.stdout.close()
    if process.stderr:
        process.stderr.close()
    assert json.dumps({"sanity": True})  # json import stays exercised
