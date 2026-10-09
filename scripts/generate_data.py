import csv
import numpy as np
from app.config import ROOT, SPEC
from app.domain import simulate

def main():
    rng=np.random.default_rng(42)
    path=ROOT/'data/training.csv'
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.writer(handle, lineterminator='\n')
        writer.writerow([item['name'] for item in SPEC['fields']]+['target'])
        for _ in range(800):
            features,target=simulate(rng)
            writer.writerow([round(float(x),6) for x in features]+[round(float(target),6)])
    print(f'Generated 800 synthetic records for {SPEC["slug"]}')

if __name__=='__main__':
    main()
