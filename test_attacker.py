import requests
import json

s = requests.Session()
r1 = s.post('http://127.0.0.1:8003/attacker/auth/login', json={'username': 'attacker', 'password': 'attack123'})
print("LOGIN:", r1.status_code, r1.text)
r2 = s.get('http://127.0.0.1:8003/attacker/users')
print("USERS:", r2.status_code, r2.text)
