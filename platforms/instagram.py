import requests
import time
from config import FB_ACCESS_TOKEN

def post_to_instagram(media_url, is_video, caption, ig_account_id, custom_token=None):
    access_token = custom_token if custom_token else FB_ACCESS_TOKEN
    if not access_token or not ig_account_id:
        return {'success': False, 'error': 'Instagram API credentials missing.'}
    
    url = f'https://graph.facebook.com/v19.0/{ig_account_id}/media'
    
    payload = {
        'access_token': access_token,
        'caption': caption
    }
    
    if is_video:
        payload['media_type'] = 'REELS'
        payload['video_url'] = media_url
    else:
        payload['image_url'] = media_url

    try:
        # Step 1: Create media container
        response = requests.post(url, data=payload)
        res_json = response.json()
        
        if 'id' not in res_json:
            return {'success': False, 'error': f"Container creation failed: {res_json}"}
            
        creation_id = res_json['id']
        
        # Step 2: Publish the container
        publish_url = f'https://graph.facebook.com/v19.0/{ig_account_id}/media_publish'
        publish_payload = {
            'creation_id': creation_id,
            'access_token': access_token
        }
        
        # Give it time for processing (both video and image)
        status_url = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code,status&access_token={access_token}"
        finished = False
        last_status = {}
        for _ in range(30): # Wait up to 150 seconds
            status_res = requests.get(status_url).json()
            last_status = status_res
            if status_res.get('status_code') == 'FINISHED':
                finished = True
                break
            elif status_res.get('status_code') == 'ERROR':
                return {'success': False, 'error': f"Instagram rejected the media: {status_res}"}
            time.sleep(5)
            
        if not finished:
            return {'success': False, 'error': f"Instagram processing timed out. Last status: {last_status}"}
            
        pub_response = requests.post(publish_url, data=publish_payload)
        pub_json = pub_response.json()
        
        if 'id' in pub_json:
             return {'success': True, 'id': pub_json['id']}
        else:
             return {'success': False, 'error': f"Publishing failed: {pub_json}"}
             
    except Exception as e:
        return {'success': False, 'error': str(e)}
