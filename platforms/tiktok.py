import requests
from config import TIKTOK_ACCESS_TOKEN, TIKTOK_OPEN_ID

def post_to_tiktok(media_path, title):
    if not TIKTOK_ACCESS_TOKEN or not TIKTOK_OPEN_ID:
        return {'success': False, 'error': 'TikTok credentials missing.'}
    
    # TikTok API requires uploading a video in chunks or providing a URL.
    # This is a simplified stub because TikTok API integration can be very complex.
    return {'success': False, 'error': 'TikTok direct API integration requires registered webhook and complex chunk uploading. Please configure properly in platforms/tiktok.py'}
