"""Closed, inert task protocols; these validators never grant free eligibility."""
from copy import deepcopy
import json
import math
import unicodedata


class RequestError(ValueError):
    def __init__(self):
        super().__init__("Unsupported free request profile.")


class ProtocolError(ValueError):
    def __init__(self):
        super().__init__("Invalid upstream task response.")


def _check(condition, error=RequestError):
    if not condition:
        raise error()


def _text(value, maximum):
    if type(value) is not str or not 1 <= len(value) <= maximum:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _integer(value, minimum, maximum):
    return type(value) is int and minimum <= value <= maximum


def _object(value, allowed, required=(), error=RequestError):
    _check(type(value) is dict and set(required) <= value.keys()
           and not (value.keys() - set(allowed)), error)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RequestError()
        result[key] = value
    return result


def _constant(_value):
    raise RequestError()


def _float(value):
    parsed = float(value)
    _check(math.isfinite(parsed))
    return parsed


def parse_json(body):
    """Read a strict JSON object, rejecting duplicate keys and nonfinite values."""
    try:
        result = json.loads(body, object_pairs_hook=_pairs, parse_constant=_constant, parse_float=_float)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise RequestError() from None
    _check(type(result) is dict)
    return result


def _strings(value, item_limit=4096, total_limit=32768):
    _check(type(value) is list and 1 <= len(value) <= 32)
    _check(all(_text(item, item_limit) for item in value))
    _check(sum(map(len, value)) <= total_limit)


def validate_request(task, payload):
    """Return a normalized copy without stripping unsupported request fields."""
    allowed = {
        "embeddings": {"model", "input", "dimensions", "encoding_format"},
        "rerank": {"model", "query", "documents", "top_n"},
        "decisions": {"model", "state", "questions"},
        "speech": {"model", "input", "voice", "response_format", "speed"},
    }
    required = {
        "embeddings": {"model", "input"},
        "rerank": {"model", "query", "documents"},
        "decisions": {"model", "state", "questions"},
        "speech": {"model", "input", "voice", "response_format"},
    }
    _check(task in allowed)
    _object(payload, allowed[task], required[task])
    model = payload["model"]
    _check(_text(model, 1024) and model.startswith("openrouter::"))
    raw_id = model.split("::", 1)[1]
    _check(_text(raw_id, 512) and not any(unicodedata.category(c).startswith("C") for c in raw_id))
    result = dict(payload)
    if task == "embeddings":
        values = payload["input"]
        _strings([values] if type(values) is str else values)
        if "dimensions" in payload:
            _check(_integer(payload["dimensions"], 1, 8192))
        _check(payload.get("encoding_format", "float") == "float")
        result["encoding_format"] = "float"
    elif task == "rerank":
        _check(_text(payload["query"], 4096))
        _strings(payload["documents"])
        _check(_integer(payload.get("top_n", len(payload["documents"])), 1, len(payload["documents"])))
        result["top_n"] = payload.get("top_n", len(payload["documents"]))
    elif task == "decisions":
        _check(_text(payload["state"], 8192))
        questions = payload["questions"]
        _check(type(questions) is dict and 1 <= len(questions) <= 8)
        for name, question in questions.items():
            _check(_text(name, 64))
            _object(question, {"type", "instructions", "criteria"}, {"type", "instructions", "criteria"})
            _check(_text(question["instructions"], 1024))
            kind, criteria = question["type"], question["criteria"]
            if kind == "choice":
                _check(type(criteria) is dict and 2 <= len(criteria) <= 16)
                _check(all(_text(k, 64) and _text(v, 512) for k, v in criteria.items()))
            elif kind == "score":
                _check(type(criteria) is list and 2 <= len(criteria) <= 16
                       and all(_text(v, 512) for v in criteria))
            elif kind == "noul":
                _check(type(criteria) is dict and set(criteria) == {"false", "true"}
                       and all(_text(v, 512) for v in criteria.values()))
            else:
                raise RequestError()
    else:
        _check(_text(payload["input"], 512) and _text(payload["voice"], 128))
        _check(payload["response_format"] in ("mp3", "pcm"))
        if "speed" in payload:
            _check(_number(payload["speed"]) and payload["speed"] == 1)
    return deepcopy(result)


def validate_capabilities(task, payload, capabilities):
    """Only explicit normalized metadata may authorize optional task parameters."""
    _check(type(capabilities) is dict)
    if task == "embeddings" and "dimensions" in payload:
        dimensions = capabilities.get("dimensions")
        _check(type(dimensions) is list and all(_integer(v, 1, 8192) for v in dimensions)
               and payload["dimensions"] in dimensions)
    if task == "speech":
        voices, formats = capabilities.get("voices"), capabilities.get("formats")
        _check(type(voices) is list and all(_text(v, 128) for v in voices)
               and payload["voice"] in voices)
        _check(type(formats) is list and all(v in ("mp3", "pcm") for v in formats)
               and payload["response_format"] in formats)


def _usage(task, data, result):
    fields = {"embeddings": ("prompt_tokens", "total_tokens"),
              "rerank": ("search_units", "total_tokens"),
              "decisions": ("input_tokens", "output_tokens")}[task]
    if "usage" not in data:
        return
    usage = data["usage"]
    _check(type(usage) is dict, ProtocolError)
    copied = {}
    for key in fields:
        if key in usage:
            _check(type(usage[key]) is int and usage[key] >= 0, ProtocolError)
            copied[key] = usage[key]
    if copied:
        result["usage"] = copied


def _probabilities(value, labels):
    _check(type(value) is dict and set(value) == set(labels), ProtocolError)
    _check(all(_number(v) and 0 <= v <= 1 for v in value.values()), ProtocolError)
    _check(abs(sum(value.values()) - 1) <= 1e-3, ProtocolError)


def validate_response(task, payload, data, raw_id):
    """Validate the full result before masking its exact model identity."""
    _check(task in {"embeddings", "rerank", "decisions"} and type(data) is dict, ProtocolError)
    _check(data.get("model") == raw_id, ProtocolError)
    result = {"model": payload["model"]}
    if "id" in data:
        _check(_text(data["id"], 1024), ProtocolError)
        result["id"] = data["id"]
    if task == "embeddings":
        count = 1 if type(payload["input"]) is str else len(payload["input"])
        rows = data.get("data")
        _check(data.get("object") == "list" and type(rows) is list and len(rows) == count, ProtocolError)
        seen, dimension, copied = set(), None, []
        for row in rows:
            _check(type(row) is dict and row.get("object") == "embedding", ProtocolError)
            index, vector = row.get("index"), row.get("embedding")
            _check(_integer(index, 0, count - 1) and index not in seen, ProtocolError)
            _check(type(vector) is list and 1 <= len(vector) <= 8192
                   and all(_number(v) for v in vector), ProtocolError)
            seen.add(index)
            if dimension is None:
                dimension = len(vector)
            _check(len(vector) == dimension and payload.get("dimensions", dimension) == dimension, ProtocolError)
            copied.append({"object": "embedding", "index": index, "embedding": [float(v) for v in vector]})
        result.update(object="list", data=sorted(copied, key=lambda item: item["index"]))
    elif task == "rerank":
        rows = data.get("results")
        count, top_n = len(payload["documents"]), payload.get("top_n", len(payload["documents"]))
        _check(type(rows) is list and len(rows) == top_n, ProtocolError)
        seen, copied = set(), []
        for row in rows:
            _check(type(row) is dict, ProtocolError)
            index, score = row.get("index"), row.get("relevance_score")
            _check(_integer(index, 0, count - 1) and index not in seen and _number(score), ProtocolError)
            seen.add(index)
            copied.append({"index": index, "relevance_score": score})
        result["results"] = copied
    else:
        answers = data.get("answers")
        _check(type(answers) is dict and set(answers) == set(payload["questions"]), ProtocolError)
        copied = {}
        for name, question in payload["questions"].items():
            answer, kind = answers[name], question["type"]
            required = {"noul": {"type", "noul"},
                        "choice": {"type", "choice", "probabilities"},
                        "score": {"type", "score", "legend", "probabilities"}}[kind]
            _object(answer, required | {"confidence"}, required, ProtocolError)
            _check(answer["type"] == kind, ProtocolError)
            if "confidence" in answer:
                _check(_number(answer["confidence"]) and 0 <= answer["confidence"] <= 1, ProtocolError)
            if kind == "noul":
                _check(_number(answer["noul"]) and 0 <= answer["noul"] <= 1, ProtocolError)
            elif kind == "choice":
                _check(type(answer["choice"]) is str and answer["choice"] in question["criteria"], ProtocolError)
                _probabilities(answer["probabilities"], question["criteria"])
            else:
                legend = {str(i): value for i, value in enumerate(question["criteria"])}
                _check(answer["legend"] == legend, ProtocolError)
                _check(_number(answer["score"]) and 0 <= answer["score"] <= len(legend) - 1, ProtocolError)
                _probabilities(answer["probabilities"], legend)
            copied[name] = deepcopy(answer)
        result["answers"] = copied
    _usage(task, data, result)
    return result


def validate_audio(payload, body, content_type):
    """Validate bounded framing only; this is not a decoder or quality claim."""
    _check(type(body) is bytes and 0 < len(body) <= 8 * 1024 * 1024, ProtocolError)
    _check(type(content_type) is str, ProtocolError)
    mime = content_type.split(";", 1)[0].strip().lower()
    if payload["response_format"] == "mp3":
        id3 = (len(body) >= 10 and body[:3] == b"ID3" and body[3] in (2, 3, 4)
               and body[4] != 255 and all(v < 128 for v in body[6:10]))
        if id3:
            size = sum(value << shift for value, shift in zip(body[6:10], (21, 14, 7, 0)))
            reserved_mask = {2: 63, 3: 31, 4: 15}[body[3]]
            id3 = size + 10 <= len(body) and not body[5] & reserved_mask
        mpeg = (len(body) >= 4 and body[0] == 255 and body[1] & 224 == 224
                and body[1] & 24 != 8 and body[1] & 6 != 0
                and body[2] & 240 != 240 and body[2] & 12 != 12)
        _check(mime == "audio/mpeg" and (id3 or mpeg), ProtocolError)
    else:
        _check(payload["response_format"] == "pcm" and mime == "audio/pcm" and len(body) % 2 == 0, ProtocolError)
        start = body.lstrip().lower()
        _check(not start.startswith((b"<html", b"<!doctype", b"<?xml")), ProtocolError)
        if start.startswith((b"{", b"[")):
            try:
                parsed = json.loads(body)
            except (ValueError, UnicodeError, RecursionError):
                parsed = None
            _check(type(parsed) not in (dict, list), ProtocolError)
    return body
