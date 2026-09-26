"""The A2A client process: call the remote agent once and print.

Run:  python examples/a2a_client.py --port 8765 --message "hello"
"""

import argparse
import asyncio

from agentscope.agent import A2AAgent
from agentscope.message import UserMsg


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--message", type=str, default="hello")
    args = parser.parse_args()

    agent = A2AAgent(endpoint=f"http://127.0.0.1:{args.port}/a2a", timeout=10)
    final = None
    async for item in agent.reply_stream(UserMsg("Alice", args.message)):
        if item.__class__.__name__ == "Msg":
            final = item
    print(f"reply: {final.get_text_content() if final else '(no reply)'}")


if __name__ == "__main__":
    asyncio.run(main())
