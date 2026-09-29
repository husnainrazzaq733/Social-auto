import os
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import YOUTUBE_CLIENT_SECRETS_FILE

# Scopes for uploading to YouTube
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    if not os.path.exists(YOUTUBE_CLIENT_SECRETS_FILE):
        return None
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        YOUTUBE_CLIENT_SECRETS_FILE, SCOPES)
    credentials = flow.run_local_server(port=0)
    return build('youtube', 'v3', credentials=credentials)

def post_to_youtube(media_path, title, description=""):
    service = get_authenticated_service()
    if not service:
         return {'success': False, 'error': 'YouTube credentials file missing.'}
         
    try:
        request_body = {
            'snippet': {
                'title': title,
                'description': description,
                'categoryId': '22'
            },
            'status': {
                'privacyStatus': 'public'
            }
        }
        
        media = MediaFileUpload(media_path, chunksize=-1, resumable=True)
        request = service.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media
        )
        
        response = request.execute()
        return {'success': True, 'id': response['id']}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
