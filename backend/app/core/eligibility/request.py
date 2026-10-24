"""Closed text-chat request contract; JSON Schema payloads remain inert data."""
import math
from copy import deepcopy


class UnsupportedFreeRequest(ValueError):
    def __init__(self):
        super().__init__("Unsupported free request profile.")


def _check(condition):
    if not condition:
        raise UnsupportedFreeRequest()


def _object(value, allowed, required=()):
    _check(isinstance(value, dict) and not (value.keys() - set(allowed)) and set(required) <= value.keys())


def _typed_fields(value, types):
    for key, kind in types.items():
        if key in value:
            _check(type(value[key]) is kind)


def validate_request(payload):
    """Validate the original JSON without logging or stripping unknown structure."""
    _object(payload, {"model", "messages", "stream", "stream_options", "temperature", "max_tokens",
        "max_completion_tokens", "top_p", "presence_penalty", "frequency_penalty", "stop", "seed", "n",
        "logprobs", "top_logprobs", "response_format", "tools", "tool_choice", "parallel_tool_calls", "user", "metadata"}, {"model", "messages"})
    _check(isinstance(payload["model"], str) and bool(payload["model"].strip()))
    _check(isinstance(payload["messages"], list))
    for message in payload["messages"]:
        _object(message, {"role", "content", "name", "tool_call_id", "tool_calls"}, {"role"})
        _typed_fields(message, {"role":str, "name":str, "tool_call_id":str})
        content = message.get("content")
        if isinstance(content, list):
            for part in content:
                _object(part, {"type", "text"}, {"type", "text"})
                _check(part["type"] == "text" and isinstance(part["text"], str))
        else:
            _check(content is None or isinstance(content, str))
        if "tool_calls" in message:
            _check(isinstance(message["tool_calls"],list))
            for tool in message["tool_calls"]:
                _object(tool, {"id", "type", "function"}, {"id", "type", "function"})
                _check(isinstance(tool["id"],str) and tool["type"]=="function")
                _object(tool["function"], {"name", "arguments"}, {"name", "arguments"})
                _typed_fields(tool["function"], {"name":str,"arguments":str})
    for field in ("temperature", "top_p", "presence_penalty", "frequency_penalty"):
        if payload.get(field) is not None:
            value=payload[field]
            _check(type(value) in (float,int) and math.isfinite(value))
    for field in ("max_tokens", "max_completion_tokens", "top_logprobs", "seed", "n"):
        if field in payload and payload[field] is not None:
            value=payload[field]
            _check(type(value) is int)
            if field in {"max_tokens", "max_completion_tokens"}: _check(value > 0)
            if field == "top_logprobs": _check(value >= 0)
            if field == "n": _check(value == 1)
        elif field in {"max_completion_tokens", "top_logprobs", "seed", "n"} and field in payload:
            raise UnsupportedFreeRequest()
    _typed_fields(payload, {"stream":bool,"logprobs":bool,"parallel_tool_calls":bool,"user":str})
    if "stop" in payload:
        value=payload["stop"]
        _check(value is None or isinstance(value,str) or (isinstance(value,list) and all(isinstance(v,str) for v in value)))
    if "stream_options" in payload:
        _object(payload["stream_options"], {"include_usage"})
        _typed_fields(payload["stream_options"], {"include_usage":bool})
    if "metadata" in payload:
        _check(isinstance(payload["metadata"],dict) and all(isinstance(k,str) and isinstance(v,str) for k,v in payload["metadata"].items()))
    if "response_format" in payload:
        value=payload["response_format"]
        _object(value, {"type", "json_schema"}, {"type"})
        _check(value["type"] in ("text", "json_object", "json_schema"))
        if value["type"] == "json_schema":
            schema=value.get("json_schema")
            _object(schema, {"name", "description", "strict", "schema"}, {"name", "schema"})
            _typed_fields(schema,{"name":str,"description":str,"strict":bool,"schema":dict})
        else: _check("json_schema" not in value)
    if "tools" in payload:
        _check(isinstance(payload["tools"],list))
        for tool in payload["tools"]:
            _object(tool,{"type","function"},{"type","function"})
            _check(tool["type"] == "function")
            function=tool["function"]
            _object(function,{"name","description","parameters","strict"},{"name"})
            _typed_fields(function,{"name":str,"description":str,"parameters":dict,"strict":bool})
    if "tool_choice" in payload:
        value=payload["tool_choice"]
        if isinstance(value,str): _check(value in ("none","auto","required"))
        else:
            _object(value,{"type","function"},{"type","function"})
            _check(value["type"]=="function")
            _object(value["function"],{"name"},{"name"})
            _typed_fields(value["function"],{"name":str})


def uses_tools(payload):
    return bool(payload.get("tools")) or "tool_choice" in payload or any(m.get("tool_calls") or m.get("role")=="tool" for m in payload.get("messages", []))


def zero_price_policy(profile):
    """Single owned definition used for both capability checks and dispatch."""
    if profile == "openrouter_zero_price":
        return {"max_price":{"prompt":"0","completion":"0","request":"0","image":"0"},"require_parameters":True}
    return None


def _valid_zero_price_policy(policy):
    if not isinstance(policy,dict) or policy.get("require_parameters") is not True:
        return False
    caps=policy.get("max_price")
    return isinstance(caps,dict) and set(caps)=={"prompt","completion","request","image"} and all(type(v) is str and v=="0" for v in caps.values())


def zero_price_policy_active(profile):
    return _valid_zero_price_policy(zero_price_policy(profile))


def prepare_dispatch(profile, payload):
    validate_request(payload)
    outbound=deepcopy(payload)
    if profile == "openrouter_zero_price":
        policy=zero_price_policy(profile)
        if not _valid_zero_price_policy(policy):
            raise UnsupportedFreeRequest()
        outbound["provider"]=policy
    return outbound
