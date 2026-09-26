# -*- coding: utf-8 -*-
"""The DeepSeek model adapter."""

from ._credential import DeepSeekCredential
from ._model import DeepSeekChatModel

__all__ = [
    "DeepSeekChatModel",
    "DeepSeekCredential",
]
