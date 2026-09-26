"""Small shared factories used by stage 1 data models, plus the JSON
argument repair shared by tool dispatch."""

import asyncio
import functools
import inspect
import json
import types
from datetime import datetime
from uuid import uuid4

from ..exception import ToolJSONDecodeError


def _generate_id() -> str:
    return uuid4().hex


def _generate_timestamp() -> str:
    return datetime.now().isoformat()


def _json_loads_with_repair(
    json_str: str,
    schema: dict | None = None,
) -> dict:
    """The given json_str maybe incomplete, e.g. '{"key', or carry arguments
    whose types don't match the schema, e.g. '{"n": "42"}', so we need to
    repair and load it into a Python object.

    .. note::
        This function is currently only used for parsing the streaming output
        of the argument field in `tool_use`, so the parsed result must be a
        dict.

    Args:
        json_str (`str`):
            The JSON string to parse, which may be incomplete or malformed.
        schema (`dict`, optional):
            An optional JSON schema to guide the repair process. The repair
            is best-effort: arguments that it cannot fix are returned
            unchanged, so that the caller's validation reports them.

    Returns:
        `dict`:
            A dictionary parsed from the JSON string after repair attempts.

    Raises:
        `ToolJSONDecodeError`:
            If the JSON string cannot be loaded into a dict.
    """
    parsed = None
    error_message = "Error: Failed to parse your tool arguments."
    try:
        # Loads directly. A valid dict still goes through the repair below
        # when a schema is given, because its argument types may be wrong.
        parsed = json.loads(json_str)
        if not isinstance(parsed, dict):
            error_message = (
                f"Error: Your argument string is decoded into a "
                f"{type(parsed)} object, but a dict object is expected!"
            )

        elif schema is None:
            return parsed
    except json.JSONDecodeError as e:
        error_message = (
            f"Error: When decoding your tool arguments from JSON format "
            f"to a Python dictionary, a JSONDecodeError was raised with "
            f"message: {str(e)}."
        )

    try:
        # Try to repair with json_repair
        from json_repair import repair_json

        try:
            res = repair_json(
                json_str,
                stream_stable=True,
                schema=schema,
                return_objects=True,
            )
        except ValueError:
            # The repair is best-effort. Leave arguments that it cannot fix
            # to the caller's schema validation, whose error message is more
            # helpful for the agent.
            res = parsed

        if isinstance(res, dict):
            if isinstance(parsed, dict) and parsed.keys() - res.keys():
                # Dropping arguments, e.g. under `additionalProperties:
                # false`, is a rewrite rather than a type repair.
                res = parsed

            try:
                # NaN and Infinity are accepted as numbers by jsonschema, but
                # silently bypass the minimum/maximum constraints.
                json.dumps(res, allow_nan=False)
            except ValueError:
                error_message = (
                    "Error: NaN and Infinity are not valid JSON numbers."
                )
            else:
                return res

    except Exception:
        # Whatever the error is, we throw the original error message to the
        # agent, which is more helpful for debugging.
        pass

    # If still failed, we throw the original error message to the agent, rather
    # than the error from json_repair, which is less helpful for debugging.
    if len(json_str) > 200:
        error_json_str = json_str[:100] + "[TRUNCATE]" + json_str[-100:]
        ellipsis_hint = (
            "(Because the JSON string is too long, a truncated label "
            '"[TRUNCATE]" is used here to indicate the truncation)'
        )
    else:
        error_json_str = json_str
        ellipsis_hint = ""

    raise ToolJSONDecodeError(
        f"""<system-reminder>{error_message}

Your argument string is decoded by the following code snippet{ellipsis_hint}:
```python
import json

your_tool_arguments = {repr(error_json_str)}
json.loads(your_tool_arguments)
```

**You should recorrect the arguments in JSON format.**</system-reminder>""",
    )


async def _is_async_func(func) -> bool:
    """Check if the given function is an async function, including
    coroutine functions, async generators, and coroutine objects.
    """

    return (
        inspect.iscoroutinefunction(func)
        or inspect.isasyncgenfunction(func)
        or isinstance(func, types.CoroutineType)
        or isinstance(func, types.GeneratorType)
        and asyncio.iscoroutine(func)
        or isinstance(func, functools.partial)
        and await _is_async_func(func.func)
    )


async def _execute_async_or_sync_func(func, *args, **kwargs):
    """Execute an async or sync function based on its type.

    Args:
        func (`Callable`):
            The function to be executed, which can be either async or sync.
        *args (`Any`):
            Positional arguments to be passed to the function.
        **kwargs (`Any`):
            Keyword arguments to be passed to the function.

    Returns:
        `Any`:
            The result of the function execution.
    """

    if await _is_async_func(func):
        return await func(*args, **kwargs)

    return func(*args, **kwargs)
