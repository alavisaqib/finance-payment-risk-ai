import json
import os
import tempfile
from pathlib import Path
from app.config import ROOT, SPEC
from app.models import fitted_model
from app.service import DecisionRequest, decide, knowledge

def main():
    os.environ['LLM_PROVIDER']='demo'
    checks=[]
    with tempfile.TemporaryDirectory() as temp:
        os.environ['STATE_DIR']=temp
        for scenario in SPEC['scenarios']:
            result=decide(DecisionRequest(features=scenario['features']))
            checks.append({'scenario':scenario['name'],'expected':scenario['expected_action'],
                'actual':result['advice']['action'],'pass':result['advice']['action']==scenario['expected_action'],
                'prompt_reduction_pct':result['optimization']['reduction_pct']})
        result=decide(DecisionRequest(features=SPEC['scenarios'][-1]['features']))
        # This is a reproducible response example, not a measured latency benchmark.
        (ROOT/'examples/response.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    retrieval=[]
    for case in json.loads((ROOT/'data/retrieval_eval.json').read_text()):
        found=knowledge().search(case['query'])
        retrieval.append({'query':case['query'],'expected_source':case['source'],
                          'hit_at_4':case['source'] in {item['source'] for item in found}})
    report={'model':fitted_model()[1],'decision_scenarios':checks,'retrieval':retrieval,
            'retrieval_hit_rate':sum(case['hit_at_4'] for case in retrieval)/len(retrieval),
            'live_llm_tested':False,'notes':'Synthetic demonstration metrics. No real-world accuracy, cost savings or production validation claimed.'}
    (ROOT/'reports').mkdir(exist_ok=True)
    (ROOT/'reports/evaluation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    if not all(case['pass'] for case in checks) or report['retrieval_hit_rate']<1:
        raise SystemExit('Evaluation gate failed')

if __name__=='__main__':
    main()
