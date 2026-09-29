import requests
from config import FB_ACCESS_TOKEN

def post_to_facebook(media_path, is_video, caption, page_id, custom_token=None):
    system_access_token = custom_token if custom_token else FB_ACCESS_TOKEN
    if not system_access_token or not page_id:
        return {'success': False, 'error': 'Facebook API credentials missing.'}
    
    # Step 1: Exchange System User Token for Page Access Token
    try:
        token_res = requests.get(f'https://graph.facebook.com/v19.0/{page_id}?fields=access_token&access_token={system_access_token}')
        token_data = token_res.json()
        if 'access_token' in token_data:
            access_token = token_data['access_token']
        else:
            # Fallback to system token if page token isn't returned (might fail with permissions error)
            access_token = system_access_token
    except Exception:
        access_token = system_access_token

    url = f'https://graph.facebook.com/v19.0/{page_id}/'
    
    try:
        if media_path is None:
            # FB Text Upload endpoint
            endpoint = f'{url}feed'
            payload = {
                'access_token': access_token,
                'message': caption
            }
            response = requests.post(endpoint, data=payload)
        elif is_video:
            # FB Video Upload endpoint
            endpoint = f'{url}videos'
            files = {'source': open(media_path, 'rb')}
            payload = {
                'access_token': access_token,
                'description': caption
            }
            response = requests.post(endpoint, data=payload, files=files)
        else:
            # FB Photo Upload endpoint
            endpoint = f'{url}photos'
            files = {'source': open(media_path, 'rb')}
            payload = {
                'access_token': access_token,
                'caption': caption
            }
            response = requests.post(endpoint, data=payload, files=files)
            
        res_json = response.json()
        if 'id' in res_json:
            return {'success': True, 'id': res_json['id']}
        else:
            return {'success': False, 'error': str(res_json)}
    except Exception as e:
        return {'success': False, 'error': str(e)}
