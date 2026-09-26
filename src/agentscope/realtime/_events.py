# -*- coding: utf-8 -*-
"""Realtime event types, ordered per turn."""
from pydantic import BaseModel


class AudioInputEvent(BaseModel):
    """One chunk of user audio, in sequence order."""

    seq: int
    data: str


class AudioOutputEvent(BaseModel):
    """One chunk of model audio to play, in sequence order."""

    seq: int
    data: str


class TranscriptDeltaEvent(BaseModel):
    """One incremental piece of the model's transcript."""

    seq: int
    delta: str


class InterruptedEvent(BaseModel):
    """The user interrupted; pending output must be dropped."""

    reason: str = "user barge-in"
