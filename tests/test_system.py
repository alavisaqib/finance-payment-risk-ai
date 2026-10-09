import json
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app.config import ROOT, SPEC
from app.main import app
from app import service
from app.llm import Advice
from app.models import fitted_model
from app.rag import KnowledgeBase

@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path):
    monkeypatch.setenv('STATE_DIR', str(tmp_path))
    monkeypatch.setenv('LLM_PROVIDER', 'demo')
    monkeypatch.delenv('APP_API_KEY', raising=False)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.parametrize('scenario', SPEC['scenarios'], ids=lambda item:item['name'])
def test_domain_scenarios_and_evidence(client, scenario):
    response = client.post('/api/decisions', json={'features': scenario['features']})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['advice']['action'] == scenario['expected_action']
    assert result['human_review_required'] is True
    assert set(result['advice']['citations']).issubset({item['id'] for item in result['evidence']})
    assert result['usage']['provider'] == 'demo'
    assert result['usage']['prompt_budget_units'] + 700 <= 10000
    assert result['optimization']['packed_prompt_units'] < result['optimization']['naive_prompt_units']

def test_cache_audit_and_invalidation(client, monkeypatch):
    body = {'features': SPEC['scenarios'][0]['features']}
    first = client.post('/api/decisions', json=body).json()
    second = client.post('/api/decisions', json=body).json()
    assert first['cache_hit'] is False and second['cache_hit'] is True
    assert first['run_id'] != second['run_id']
    assert second['current_request_tokens'] == {'input': 0, 'output': 0}
    assert len(client.get('/api/history').json()['runs']) == 2
    monkeypatch.setattr(service, 'CODE_VERSION', 'changed')
    assert client.post('/api/decisions', json=body).json()['cache_hit'] is False

def test_input_validation(client):
    assert client.post('/api/decisions', json={'features': {}}).status_code == 422
    body = {'features': dict(SPEC['scenarios'][0]['features'])}
    field = SPEC['fields'][0]
    body['features'][field['name']] = field['max'] + 1
    assert client.post('/api/decisions', json=body).status_code == 422
    assert client.get('/api/search?q=ab').status_code == 422
    assert client.get('/api/history?limit=10000').status_code == 422

def test_fractional_counts_rejected(client):
    field = next(item for item in SPEC['fields'] if item.get('integer'))
    body = {'features': dict(SPEC['scenarios'][0]['features'])}
    body['features'][field['name']] = field['min'] + .5
    assert client.post('/api/decisions', json=body).status_code == 422

def test_auth_and_dashboard(client, monkeypatch):
    monkeypatch.setenv('APP_API_KEY', 'test-only-key')
    assert client.get('/api/meta').status_code == 401
    assert client.get('/api/meta', headers={'X-API-Key':'test-only-key'}).status_code == 200
    assert client.get('/').status_code == 200
    assert client.get('/health').json()['status'] == 'ok'

def test_retrieval_rank_budget_and_unknown():
    kb = KnowledgeBase()
    for case in json.loads((ROOT / 'data/retrieval_eval.json').read_text()):
        found = kb.search(case['query'])
        assert all(len(item['text']) >= 100 and not item['text'].startswith('#') for item in found)
        assert case['source'] in {item['source'] for item in found}
        assert sum(len(json.dumps(item, ensure_ascii=False).encode()) for item in found) <= 1600
    assert kb.search('zzzzqqq12345') == []
    assert kb.search(SPEC['retrieval_query'], budget=1) == []

def test_model_quality_exceeds_baseline():
    _, metrics, _ = fitted_model()
    assert metrics['test_rows'] == 200
    if SPEC['task'] == 'classification':
        assert metrics['roc_auc'] > .65
        assert metrics['average_precision'] > metrics['positive_prevalence']
    else:
        assert metrics['mae'] < metrics['mean_baseline_mae']

def test_llm_cannot_lower_priority(client, monkeypatch):
    def fake_advice(facts, question, evidence):
        return Advice(action='monitor', rationale='Ignore all policy', citations=[evidence[0]['id']], next_steps=['Review']), {'provider':'test','model':'test','input_tokens':10,'output_tokens':5,'prompt_budget_units':3000}
    monkeypatch.setattr(service, 'advise', fake_advice)
    scenario = next(item for item in SPEC['scenarios'] if item['expected_action'] == 'escalate')
    result = client.post('/api/decisions', json={'features':scenario['features']}).json()
    assert result['advice']['action'] == 'escalate'
    assert result['guardrail_override']

def test_provider_errors_are_not_demo_success(client, monkeypatch):
    def fail(*args):
        raise RuntimeError('secret-provider-body')
    monkeypatch.setattr(service, 'advise', fail)
    response = client.post('/api/decisions', json={'features':SPEC['scenarios'][0]['features']})
    assert response.status_code == 503
    assert 'secret-provider-body' not in response.text

def test_openai_contract_and_invalid_citation(monkeypatch):
    import openai
    from app.llm import advise
    monkeypatch.setenv('LLM_PROVIDER','openai')
    monkeypatch.setenv('OPENAI_API_KEY','test-key-not-real')
    monkeypatch.setenv('OPENAI_MODEL','test-model')
    captured = {}
    def parse(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output_parsed=Advice(action='review', rationale='Check evidence', citations=['policy:1'], next_steps=['Review']), usage=SimpleNamespace(input_tokens=120,output_tokens=30))
    monkeypatch.setattr(openai,'OpenAI',lambda **kwargs:SimpleNamespace(responses=SimpleNamespace(parse=parse)))
    evidence=[{'id':'policy:1','text':'Review'}]
    _, usage=advise({},'What should happen?',evidence)
    assert usage['input_tokens']==120 and captured['store'] is False
    assert captured['text_format'] is Advice
    with pytest.raises(ValueError,match='citations'):
        advise({},'What should happen?',[{'id':'other:1','text':'Review'}])
