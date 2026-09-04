from fastapi.testclient import TestClient
from backend.app.main import app
client=TestClient(app)
def test_root(): assert client.get('/').status_code==200
def test_health(): assert client.get('/api/v1/health').json()['status']=='ok'
def test_demo():
 r=client.post('/api/v1/demo/seed'); assert r.status_code==200; assert r.json()['severity'] in ['LOW','MEDIUM','HIGH','CRITICAL']
