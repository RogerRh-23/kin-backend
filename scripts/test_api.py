Okfrom fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print('Testing register...')
resp = client.post('/auth/register', json={"username":"ci_user","email":"ci_user@local","password":"pass123","role":"user"})
print('register status:', resp.status_code, resp.text)

print('Testing login...')
resp = client.post('/auth/login', json={"username":"ci_user","password":"pass123"})
print('login status:', resp.status_code, resp.text)
if resp.status_code == 200:
    token = resp.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}'}
    print('Testing protected empleados...')
    resp2 = client.get('/empleados/', headers=headers)
    print('empleados status:', resp2.status_code, resp2.text)
else:
    print('login failed, skipping protected test')
