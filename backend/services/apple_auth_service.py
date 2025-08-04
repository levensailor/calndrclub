import httpx
import time
from jose import jwt
from core.config import settings
from core.logging import logger

def _generate_client_secret():
    headers = {"kid": settings.APPLE_KEY_ID}
    payload = {
        "iss": settings.APPLE_TEAM_ID,
        "iat": int(time.time()),
        "exp": int(time.time()) + 60 * 60 * 6,  # 6 months
        "aud": "https://appleid.apple.com",
        "sub": settings.APPLE_CLIENT_ID,
    }
    return jwt.encode(payload, settings.APPLE_PRIVATE_KEY, algorithm="ES256", headers=headers)

async def exchange_code(code: str):
    client_secret = _generate_client_secret()
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'client_id': settings.APPLE_CLIENT_ID,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': settings.APPLE_REDIRECT_URI,
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post('https://appleid.apple.com/auth/token', data=data, headers=headers)
        
        if resp.status_code != 200:
            logger.error(f"Apple token exchange failed: {resp.status_code} - {resp.text}")
            resp.raise_for_status()
            
        return resp.json() 