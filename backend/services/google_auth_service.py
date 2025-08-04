import httpx
from core.config import settings
from core.logging import logger

GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo'

async def exchange_code(code: str):
    data = {
        'code': code,
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data=data)
        
        if resp.status_code != 200:
            logger.error(f"Google token exchange failed: {resp.status_code} - {resp.text}")
            resp.raise_for_status()
            
        return resp.json()

async def get_user_info(id_token: str):
    headers = {'Authorization': f'Bearer {id_token}'}
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(GOOGLE_USERINFO_URL, headers=headers)
        
        if resp.status_code != 200:
            logger.error(f"Failed to get Google user info: {resp.status_code} - {resp.text}")
            resp.raise_for_status()
            
        return resp.json() 