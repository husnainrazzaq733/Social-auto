import requests
from config import FB_ACCESS_TOKEN
import sys

def check_page(page_id):
    url = f'https://graph.facebook.com/v19.0/{page_id}?fields=access_token'
    params = {'access_token': FB_ACCESS_TOKEN}
    res = requests.get(url, params=params)
    print(f"{page_id}: {res.json()}")

check_page('1233388619868471') # Next Gen
check_page('1328264507042017') # Test 2
