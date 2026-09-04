from urllib.request import Request,urlopen
req=Request('http://127.0.0.1:8000/api/v1/demo/seed',method='POST')
print(urlopen(req,timeout=5).read().decode())
