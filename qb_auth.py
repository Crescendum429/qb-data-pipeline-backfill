import requests
import base64

def get_access_token(client_id, client_secret, refresh_token):
    # obtenre el token 
    token_url = 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer'
    
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    
    response = requests.post(token_url, headers=headers, data=data)
    
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f"Error getting token: {response.text}")

if __name__ == '__main__':
    # prueba 
    import os
    
    client_id = os.getenv('QB_CLIENT_ID')
    client_secret = os.getenv('QB_CLIENT_SECRET') 
    refresh_token = os.getenv('QB_REFRESH_TOKEN')
    
    if client_id and client_secret and refresh_token:
        token = get_access_token(client_id, client_secret, refresh_token)
        print(f"Access token: {token[:20]}...")
    else:
        print("Configurar variables QB_CLIENT_ID, QB_CLIENT_SECRET, QB_REFRESH_TOKEN")
