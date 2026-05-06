from __future__ import annotations

from dataclasses import dataclass


OVERSEAS_BASE_URL = 'https://eval.dashscope.aliyuncs.com/compatible-mode/v1'
DOMESTIC_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
DEFAULT_COMPAT_MAX_TOKENS = 1024


@dataclass(frozen=True)
class ApiModelConfig:
    model_name: str
    endpoint: str
    input_field: str = 'messages'
    need_max_tokens: bool = False
    aliases: tuple[str, ...] = ()


API_MODEL_CONFIGS: tuple[ApiModelConfig, ...] = (
    ApiModelConfig(
        'openai.gpt-5.4-2026-03-05',
        'overseas',
        aliases=('gpt-5.4',),
    ),
    ApiModelConfig(
        'openai.gpt-5.4-pro-2026-03-05',
        'overseas',
        input_field='input',
        need_max_tokens=True,
        aliases=('gpt-5.4-pro',),
    ),
    ApiModelConfig(
        'aws.claude-sonnet-4-6',
        'overseas',
        need_max_tokens=True,
        aliases=('claude-sonnet-4-6', 'vertex_ai.claude-sonnet-4-6'),
    ),
    ApiModelConfig(
        'aws.claude-opus-4-6',
        'overseas',
        need_max_tokens=True,
        aliases=('claude-opus-4-6', 'vertex_ai.claude-opus-4-6'),
    ),
    ApiModelConfig(
        'aws.claude-opus-4-5-20251101',
        'overseas',
        need_max_tokens=True,
        aliases=('claude-opus-4-5-20251101', 'vertex_ai.claude-opus-4-5-20251101'),
    ),
    ApiModelConfig(
        'vertex_ai.gemini-3.1-pro-preview',
        'overseas',
        input_field='contents',
        aliases=('gemini-3.1-pro-preview', 'ai_studio.gemini-3.1-pro-preview'),
    ),
    ApiModelConfig(
        'grok-4-1-fast-reasoning',
        'overseas',
        aliases=('grok-4-1-fast-non-reasoning',),
    ),
    ApiModelConfig('glm-4.7-inner', 'overseas'),
    ApiModelConfig('glm-image', 'overseas'),
    ApiModelConfig(
        'z_ai.glm-5',
        'overseas',
        aliases=('glm-5',),
    ),
    ApiModelConfig('qwen3.6-max-preview', 'domestic'),
    ApiModelConfig('qwen3.6-plus', 'domestic'),
    ApiModelConfig(
        'deepseek-v4-pro',
        'domestic',
        aliases=('deepseek.deepseek-v4-pro',),
    ),
    ApiModelConfig(
        'deepseek-v4-flash',
        'domestic',
        aliases=('deepseek.deepseek-v4-flash', 'deepseek_v4_flash'),
    ),
    ApiModelConfig(
        'kimi-k2.6',
        'domestic',
        aliases=('moonshot.kimi-k2.6',),
    ),
    ApiModelConfig('glm-5.1', 'domestic'),
    ApiModelConfig('xiaomi.mimo-v2.5', 'domestic'),
)


_MODEL_LOOKUP: dict[str, ApiModelConfig] = {}
for _cfg in API_MODEL_CONFIGS:
    for _name in (_cfg.model_name, *_cfg.aliases):
        _MODEL_LOOKUP[_name.strip().casefold()] = _cfg


def get_api_model_config(model_name: str | None) -> ApiModelConfig | None:
    if not model_name:
        return None
    return _MODEL_LOOKUP.get(model_name.strip().casefold())


def resolve_api_model_name(model_name: str | None, *, default: str) -> str:
    candidate = (model_name or default).strip()
    cfg = get_api_model_config(candidate)
    return cfg.model_name if cfg is not None else candidate


def default_base_url_for_model(model_name: str | None) -> str | None:
    cfg = get_api_model_config(model_name)
    if cfg is None:
        return None
    if cfg.endpoint == 'overseas':
        return OVERSEAS_BASE_URL
    return DOMESTIC_BASE_URL
