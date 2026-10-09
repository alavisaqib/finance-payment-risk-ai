import hashlib
import json
import os
import time
import uuid
from functools import lru_cache
from pydantic import BaseModel, ConfigDict, Field, field_validator
from . import storage
from .config import ROOT, SPEC
from .domain import analyze
from .llm import advise, budget_units, payload_for
from .models import fitted_model
from .rag import KnowledgeBase

class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    features: dict[str, float]
    question: str = Field(default='Explain the recommended operational action and supporting policy.', min_length=3, max_length=700)
    context_budget: int = Field(default=1600, ge=1000, le=2400)

    @field_validator('features')
    @classmethod
    def validate_features(cls, values):
        expected = {item['name']: item for item in SPEC['fields']}
        if set(values) != set(expected):
            raise ValueError('Supply exactly these features: ' + ', '.join(expected))
        for name, value in values.items():
            item = expected[name]
            if not item['min'] <= value <= item['max']:
                raise ValueError(f'{name} must be between {item["min"]} and {item["max"]}')
            if item.get('integer') and value != int(value):
                raise ValueError(f'{name} must be an integer')
        return values

@lru_cache(maxsize=1)
def knowledge():
    return KnowledgeBase()

def version():
    digest = hashlib.sha256()
    for path in sorted((ROOT / 'app').glob('*.py')) + [ROOT / 'project.json', ROOT / 'data/training.csv']:
        digest.update(path.read_bytes())
    return digest.hexdigest()

CODE_VERSION = version()

def decide(request: DecisionRequest):
    started = time.perf_counter()
    kb = knowledge()
    provider = os.getenv('LLM_PROVIDER', 'demo')
    identity = {'request': request.model_dump(), 'corpus': kb.version, 'code': CODE_VERSION,
                'provider': provider, 'model': os.getenv('OPENAI_MODEL', '')}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    result = storage.cached(key)
    hit = result is not None
    if not hit:
        facts = analyze(request.features)
        evidence = kb.search(SPEC['retrieval_query'] + ' ' + request.question + ' ' + facts['summary'], budget=request.context_budget)
        if not evidence:
            raise ValueError('No relevant evidence fits the context budget')
        advice, usage = advise(facts, request.question, evidence)
        priorities = {'monitor': 0, 'review': 1, 'escalate': 2}
        proposed = advice.action
        advice.action = max([advice.action, facts['minimum_action']], key=priorities.get)
        full = budget_units(payload_for(facts, request.question, kb.chunks))
        result = {'project': SPEC['title'], 'facts': facts, 'advice': advice.model_dump(),
                  'guardrail_override': proposed != advice.action, 'evidence': evidence,
                  'usage': usage, 'optimization': {'naive_prompt_units': full,
                  'packed_prompt_units': usage['prompt_budget_units'],
                  'reduction_pct': round(100 * (1 - usage['prompt_budget_units'] / full), 1),
                  'measurement': 'UTF-8 text byte upper bound plus framing; not billed tokens'},
                  'corpus_version': kb.version, 'code_version': CODE_VERSION,
                  'features': request.features, 'human_review_required': True}
    result['run_id'] = str(uuid.uuid4())
    result['cache_hit'] = hit
    result['current_request_tokens'] = {'input': 0 if hit else result['usage']['input_tokens'],
                                        'output': 0 if hit else result['usage']['output_tokens']}
    result['latency_ms'] = round((time.perf_counter() - started) * 1000, 2)
    storage.record(key, result)
    return result

def metadata():
    return {**SPEC, 'model_metrics': fitted_model()[1], 'provider': os.getenv('LLM_PROVIDER', 'demo')}
