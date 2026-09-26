"""Credential data for OpenAI-compatible Chat Completions APIs."""

from typing import Literal

from pydantic import BaseModel, SecretStr


class OpenAICredential(BaseModel):
    type: Literal["openai_credential"] = "openai_credential"
    api_key: SecretStr
    organization: str | None = None
    base_url: str | None = None
