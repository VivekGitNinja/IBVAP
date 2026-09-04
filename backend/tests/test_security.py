from backend.app.core.security import hash_password,verify_password,create_access_token,decode_access_token
def test_password():
 h=hash_password('secret'); assert verify_password('secret',h); assert not verify_password('bad',h)
def test_jwt():
 p=decode_access_token(create_access_token('operator','OPERATOR')); assert p['sub']=='operator'; assert p['role']=='OPERATOR'
