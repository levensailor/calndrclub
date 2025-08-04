import facebook
from core.config import settings

async def get_user_info(access_token: str):
    """
    Get user info from Facebook using the access token.
    """
    try:
        graph = facebook.GraphAPI(access_token=access_token)
        profile = graph.get_object('me', fields='id,name,email,first_name,last_name')
        return profile
    except facebook.GraphAPIError as e:
        print(f"Facebook GraphAPIError: {e}")
        return None
