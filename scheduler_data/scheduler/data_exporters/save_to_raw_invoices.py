from mage_ai.settings.repo import get_repo_path
from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.postgres import Postgres
from pandas import DataFrame
from os import path
import pandas as pd

@data_exporter
def save_to_raw_invoices(df: DataFrame, **kwargs) -> None:
    schema_name = 'raw'
    table_name = 'qb_invoices'
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    config_profile = 'default'
    
    if len(df) == 0:
        print("No records to process")
        return
    
    df = df[df['id'].notnull()]
    df = df.drop_duplicates(subset=['id'])
    
    fecha_inicio = kwargs.get('fecha_inicio', '2025-01-01')
    fecha_fin = kwargs.get('fecha_fin', '2025-09-16')
    
    timestamp_columns = ['ingested_at_utc', 'extract_window_start_utc', 'extract_window_end_utc']
    
    for col in timestamp_columns:
        if col in df.columns:
            if col == 'ingested_at_utc':
                df[col] = pd.Timestamp.now(tz='UTC')
            elif col == 'extract_window_start_utc':
                df[col] = pd.Timestamp(fecha_inicio, tz='UTC')
            elif col == 'extract_window_end_utc':
                df[col] = pd.Timestamp(fecha_fin, tz='UTC')
    
    if 'page_number' in df.columns:
        df['page_number'] = df['page_number'].astype(int)
    if 'page_size' in df.columns:
        df['page_size'] = df['page_size'].astype(int)
    
    if 'payload' in df.columns:
        df['payload'] = df['payload'].astype(str)
    if 'request_payload' in df.columns:
        df['request_payload'] = df['request_payload'].astype(str)
    
    with Postgres.with_config(ConfigFileLoader(config_path, config_profile)) as loader:
        try:
            if len(df) > 0:
                ids_str = "','".join(df['id'].astype(str).tolist())
                existing_query = f"SELECT id FROM {schema_name}.{table_name} WHERE id IN ('{ids_str}')"
                
                existing_records = loader.load(existing_query)
                existing_ids = set(existing_records['id'].tolist()) if len(existing_records) > 0 else set()
                
                new_records_df = df[~df['id'].isin(existing_ids)]
                
                if len(new_records_df) > 0:
                    loader.export(new_records_df, schema_name, table_name, index=False, if_exists='append', allow_reserved_words=True)
                    print(f"Inserted {len(new_records_df)} new invoices")
                else:
                    print("All invoices already exist")
                    
        except Exception as e:
            print(f"Error during insert: {e}")
            loader.export(df, schema_name, table_name, index=False, if_exists='append', allow_reserved_words=True)
    
    print("Export completed")