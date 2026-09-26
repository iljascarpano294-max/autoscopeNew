# -*- coding: utf-8 -*-
"""DeepSeek credential: an OpenAI-compatible credential with the
DeepSeek base URL as default."""
from typing import Literal

from ...credential import OpenAICredential


class DeepSeekCredential(OpenAICredential):
    type: Literal["deepseek_credential"] = "deepseek_credential"
    base_url: str = "https://api.deepseek.com"
