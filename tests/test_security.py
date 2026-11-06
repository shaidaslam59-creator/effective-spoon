from security.authentication import APIKeyAuthenticator

def test_api_key_verification():
    auth = APIKeyAuthenticator(["correct-key"])
    assert auth.verify("correct-key")
    assert not auth.verify("wrong-key")
    assert not auth.verify(None)
