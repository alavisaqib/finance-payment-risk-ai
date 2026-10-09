import math
from .models import predict
from .config import SPEC

def transform(features):
    return [features[name] for name in SPEC['model_features']]

def result(action, summary, signals, steps):
    return {'minimum_action':action, 'summary':summary, 'signals':signals, 'next_steps':steps}

def analyze(f):
    probability,_=predict(f)
    high=f['transactions_1h']>=15 or (f['transactions_1h']>=5 and f['account_age_days']<7)
    action='escalate' if high else 'review' if f['transactions_1h']>=5 or f['distance_km']>1000 or probability>.65 else 'monitor'
    return result(action, f'Investigation risk score {probability:.1%}; {int(f["transactions_1h"])} transactions in the last hour.',
        {'risk_probability':round(probability,3),'transactions_last_hour':int(f['transactions_1h']),'account_age_days':int(f['account_age_days'])},
        ['Corroborate velocity and location with source transaction evidence.', 'Have the payment-risk analyst review the case; no payment or account action is executed.'])

def simulate(rng):
    amount=rng.uniform(10,10000); velocity=int(rng.integers(1,26)); age=int(rng.integers(0,1500)); distance=rng.uniform(0,4000)
    p=1/(1+math.exp(-(-5+.00015*amount+.2*velocity-.002*age+.00065*distance)))
    return [amount,velocity,age,distance], int(rng.random()<p)
