import requests
import json
import pandas as pd
from datetime import datetime, timezone
from mage_ai.data_preparation.shared.secrets import get_secret_value
import time

@data_loader
def extract_qb_invoices(*args, **kwargs):
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
    
    all_invoices = []
    start_position = 1
    page_size = 100
    
    while True:
        query = "SELECT * FROM Invoice"
        
        params = {
            'query': query,
            'startPosition': start_position,
            'maxResults': page_size
        }
        
        response = requests.get(f"{base_url}/query", headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        invoices = data.get('QueryResponse', {}).get('Invoice', [])
        
        if not invoices:
            break
        
        all_invoices.extend(invoices)
        start_position += page_size
        
        if len(invoices) < page_size:
            break
            
        time.sleep(0.5)
    
    filtered_invoices = []
    for invoice in all_invoices:
        txn_date = invoice.get('TxnDate', '')
        last_updated = invoice.get('MetaData', {}).get('LastUpdatedTime', '')
        
        filter_date = txn_date if txn_date else last_updated[:10] if last_updated else ''
        
        if filter_date and fecha_inicio <= filter_date <= fecha_fin:
            filtered_invoices.append(invoice)
    
    processed_records = []
    current_time = datetime.now(timezone.utc)
    
    for invoice in filtered_invoices:
        processed_record = {
            'id': invoice.get('Id'),
            'payload': json.dumps(invoice),
            'ingested_at_utc': current_time,
            'extract_window_start_utc': fecha_inicio,
            'extract_window_end_utc': fecha_fin,
            'page_number': 1,
            'page_size': len(filtered_invoices),
            'request_payload': json.dumps({
                'entity_type': 'invoices',
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