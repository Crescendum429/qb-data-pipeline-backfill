import requests
import json
import pandas as pd
from datetime import datetime, timezone
from mage_ai.data_preparation.shared.secrets import get_secret_value
import time

@data_loader
def extract_qb_customers(*args, **kwargs):
    client_id = get_secret_value('QB_CLIENT_ID')
    client_secret = get_secret_value('QB_CLIENT_SECRET')
    realm_id = get_secret_value('QB_REALM_ID')
    refresh_token = get_secret_value('QB_REFRESH_TOKEN')
    environment = get_secret_value('QB_ENVIRONMENT')
    
    fecha_inicio = kwargs.get('fecha_inicio', '2025-01-01')
    fecha_fin = kwargs.get('fecha_fin', '2025-09-16')
    
    access_token = get_access_token(client_id, client_secret, refresh_token)
    
    if environment.lower() == 'sandbox':
        base_url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}"
    else:
        base_url = f"https://quickbooks.api.intuit.com/v3/company/{realm_id}"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    all_customers = []
    start_position = 1
    page_size = 100
    
    while True:
        query = "SELECT * FROM Customer"
        
        params = {
            'query': query,
            'startPosition': start_position,
            'maxResults': page_size
        }
        
        response = requests.get(f"{base_url}/query", headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        customers = data.get('QueryResponse', {}).get('Customer', [])
        
        if not customers:
            break
        
        all_customers.extend(customers)
        start_position += page_size
        
        if len(customers) < page_size:
            break
            
        time.sleep(0.5)
    
    filtered_customers = []
    for customer in all_customers:
        last_updated = customer.get('MetaData', {}).get('LastUpdatedTime', '')
        if last_updated:
            customer_date = last_updated[:10]
            if fecha_inicio <= customer_date <= fecha_fin:
                filtered_customers.append(customer)
    
    processed_records = []
    current_time = datetime.now(timezone.utc)
    
    for customer in filtered_customers:
        processed_record = {
            'id': customer.get('Id'),
            'payload': json.dumps(customer),
            'ingested_at_utc': current_time,
            'extract_window_start_utc': fecha_inicio,
            'extract_window_end_utc': fecha_fin,
            'page_number': 1,
            'page_size': len(filtered_customers),
            'request_payload': json.dumps({
                'entity_type': 'customers',
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'environment': environment
            })
        }
        processed_records.append(processed_record)
    
    return pd.DataFrame(processed_records)


def get_access_token(client_id, client_secret, refresh_token):
    import base64
    
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