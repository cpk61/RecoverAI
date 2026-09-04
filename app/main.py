from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from .core import bootstrap

app=FastAPI(title='RecoverAI - Bounded Revenue Recovery Agent')
BASE=Path(__file__).resolve().parent
templates=Jinja2Templates(directory=str(BASE/'templates'))
DF,MODEL,METRICS,SUMMARY,AUDIT=bootstrap()

@app.get('/health')
def health(): return {'status':'ok','project':'RecoverAI'}

@app.get('/',response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse('index.html',{
        'request':request,'metrics':METRICS,'summary':SUMMARY,'audit':AUDIT[:12]
    })

@app.get('/api/metrics')
def metrics(): return METRICS

@app.get('/api/summary')
def summary(): return SUMMARY

@app.get('/api/audit')
def audit(limit:int=50): return AUDIT[:max(1,min(limit,200))]
