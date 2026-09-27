import requests
import json
try:
    res = requests.post("http://localhost:8000/suggest_options", json={"context": "pizza, tomato, pasta"})
    print(res.json())
except Exception as e:
    print(e)
