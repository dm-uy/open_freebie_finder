"""Strict visible text qualification; ordinary delivery remains more permissive."""
from dataclasses import dataclass
import json
from backend.app.core.adapters.openai_client import valid_completion


@dataclass(frozen=True)
class ProbeOutcome:
    passed: bool = False
    status: int | None = None
    code: str = 'probe_inconclusive'
    completion_tokens: int | None = None
    cost_status: str = 'unavailable'
    retry_after: str | None = None
    diagnostics: dict | None = None


class ProbeProtocol:
    def __init__(self):
        self.visible = False
        self.terminal = 0
        self.done = 0
        self.invalid = False
        self.tokens = None

    def usage(self, data):
        usage = data.get('usage')
        if isinstance(usage, dict) and 'completion_tokens' in usage:
            value = usage['completion_tokens']
            if type(value) is not int or not 0 <= value <= 32:
                self.invalid = True
            else:
                self.tokens = value

    def message(self, value):
        if not isinstance(value, dict):
            self.invalid = True
            return
        content = value.get('content')
        if content is not None and not isinstance(content, str):
            self.invalid = True
        if isinstance(content, str) and content.strip():
            self.visible = True
        if any(value.get(k) for k in ('tool_calls', 'function_call', 'audio', 'images', 'image', 'video')):
            self.invalid = True
        if value.get('role', 'assistant') != 'assistant':
            self.invalid = True

    def buffered(self, data):
        if not valid_completion(data):
            self.invalid = True
            return
        self.usage(data)
        choice = data['choices'][0]
        self.message(choice['message'])
        self.terminal = int(choice.get('finish_reason') in ('stop', 'length'))
        self.done = 1

    def event(self, value):
        if value == '[DONE]':
            self.done += 1
            return
        if self.done:
            self.invalid = True
        data = json.loads(value)
        if not isinstance(data, dict) or 'error' in data:
            self.invalid = True
            return data
        self.usage(data)
        choices = data.get('choices')
        if not isinstance(choices, list) or len(choices) > 1:
            self.invalid = True
            return data
        if self.terminal and choices:
            self.invalid = True
        if choices:
            choice = choices[0]
            if not isinstance(choice, dict) or type(choice.get('index', 0)) is not int or choice.get('index', 0) != 0:
                self.invalid = True
                return data
            self.message(choice.get('delta', {}))
            if choice.get('finish_reason') is not None:
                if choice['finish_reason'] not in ('stop', 'length'):
                    self.invalid = True
                self.terminal += 1
        return data

    @property
    def passed(self):
        return self.visible and self.terminal == 1 and self.done == 1 and not self.invalid


def safe_probe_diagnostics(data, *, non_json_body=None):
    """Fixed shape/phrase codes only; never retain upstream text, IDs or keys.

    NVIDIA's function-not-found phrase is diagnostic, not a billing classifier
    or an admission decision. Unknown bodies remain unknown.
    """
    import re
    def kind(value):
        return {dict:'object',list:'array',str:'string',int:'integer',float:'number',bool:'boolean',type(None):'null'}.get(type(value),'other')
    result={'body_kind':'non_json' if non_json_body is not None else kind(data)}
    fragments=[]
    if isinstance(data,dict):
        error=data.get('error')
        result['error_kind']=kind(error)
        if isinstance(error,dict):
            fragments.extend(error.get(k) for k in ('message','detail','title'))
        elif isinstance(error,str):fragments.append(error)
        fragments.extend(data.get(k) for k in ('detail','title','message'))
        choices=data.get('choices')
        result['choices_kind']=kind(choices)
        if isinstance(choices,list):
            result['choices_count']=min(len(choices),1001)
            if len(choices)==1 and isinstance(choices[0],dict):
                choice=choices[0]
                finish=choice.get('finish_reason')
                result['finish_reason']=finish if isinstance(finish,str) and finish in {'stop','length','model_length','error','tool_calls','function_call','content_filter'} else 'null' if finish is None else 'other'
                message=choice.get('message',choice.get('delta'))
                result['message_kind']=kind(message)
                if isinstance(message,dict):
                    result['content_kind']=kind(message.get('content'))
                    result['tool_calls_kind']=kind(message.get('tool_calls'))
                    result['visible_text']=isinstance(message.get('content'),str) and bool(message['content'].strip())
        usage=data.get('usage')
        result['usage_kind']=kind(usage)
        if isinstance(usage,dict):result['completion_tokens_kind']=kind(usage.get('completion_tokens'))
    elif isinstance(data,str):fragments.append(data)
    if non_json_body is not None:
        fragments.append(non_json_body[:4096].decode('utf-8',errors='replace'))
    text=' '.join(v[:4096] for v in fragments if isinstance(v,str)).lower()
    if re.search(r'\bfunction\b.{0,160}\bnot found for account\b',text):
        result['error_contract']='function_not_found_for_account'
    elif text.strip()=='404 page not found':result['error_contract']='plain_page_not_found'
    elif text.strip() in {'not found','404 not found'}:result['error_contract']='generic_not_found'
    return result
