"""Show which checkout supplies the installed agentscope package."""

import agentscope


if __name__ == "__main__":
    print(f"AgentScope version: {agentscope.__version__}")
    print(f"Imported from: {agentscope.__file__}")
