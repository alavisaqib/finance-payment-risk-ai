import os
import secrets
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .config import ROOT, SPEC
from .service import DecisionRequest, decide, knowledge, metadata
from .storage import history

app = FastAPI(title=SPEC['title'], version='1.0.0', description=SPEC['problem'])
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

def authenticate(x_api_key: str = Header(default='')):
    expected = os.getenv('APP_API_KEY', '')
    if expected and not secrets.compare_digest(expected, x_api_key):
        raise HTTPException(status_code=401, detail='A valid X-API-Key header is required')

@app.get('/')
def dashboard():
    return FileResponse(ROOT / 'static/index.html')

@app.get('/health')
def health():
    return {'status': 'ok', 'project': SPEC['slug']}

@app.get('/api/meta', dependencies=[Depends(authenticate)])
def meta():
    return metadata()

@app.post('/api/decisions', dependencies=[Depends(authenticate)])
def decision(request: DecisionRequest):
    try:
        return decide(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        # Do not return provider bodies, keys, prompts, or filesystem paths.
        raise HTTPException(status_code=503, detail='Decision service unavailable; inspect server configuration and retry.') from error

@app.get('/api/search', dependencies=[Depends(authenticate)])
def search(q: str = Query(min_length=3, max_length=700)):
    return {'results': knowledge().search(q)}

@app.get('/api/history', dependencies=[Depends(authenticate)])
def audit(limit: int = Query(default=20, ge=1, le=100)):
    return {'runs': history(limit)}
