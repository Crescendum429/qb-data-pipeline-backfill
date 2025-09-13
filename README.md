# QuickBooks Online Data Pipeline - Backfill Histórico

## Descripción

Este proyecto implementa un pipeline de datos para extraer información histórica de QuickBooks Online (QBO) para las entidades Customers, Invoices e Items, depositándola en PostgreSQL usando Mage como orquestador.

## Arquitectura del Sistema

```
QuickBooks Online API (OAuth 2.0) ->   Mage AI (Orquestador)->    PostgreSQL (Schema raw) ->    PgAdmin (UI)
```

### Componentes

- **Origen**: QuickBooks Online API con autenticación OAuth 2.0
- **Orquestación**: Mage AI con pipelines parametrizados
- **Almacenamiento**: PostgreSQL con esquema raw
- **Administración**: PgAdmin para gestión de base de datos
- **Despliegue**: Docker Compose

## Configuración del Proyecto

### Prerequisitos

- Docker y Docker Compose instalados
- Credenciales de QuickBooks Online (sandbox)
- Client ID, Client Secret, Realm ID y Refresh Token válidos

### Levantar el Entorno

1. Clonar el repositorio
2. Ejecutar Docker Compose:

```bash
docker-compose up -d
```

3. Verificar que los servicios estén corriendo:

```bash
docker ps
```

### Acceso a Servicios

- **Mage**: http://localhost:6789
- **PgAdmin**: http://localhost:8080
  - Email: admin@admin.com
  - Password: root

### Inicializar Base de Datos

```bash
docker exec -i <postgres_container> psql -U root -d qb_data < init_qb_schema.sql
```

## Gestión de Secretos

Todos los valores sensibles se gestionan a través de Mage Secrets. Ningún secreto debe exponerse en código o variables de entorno.

### Secretos Requeridos

**QuickBooks Online:**
- `QB_CLIENT_ID`: Identificador de la aplicación QB
- `QB_CLIENT_SECRET`: Clave secreta de la aplicación QB
- `QB_REALM_ID`: ID de la empresa en QuickBooks
- `QB_REFRESH_TOKEN`: Token de actualización OAuth2
- `QB_ENVIRONMENT`: sandbox o production

**PostgreSQL:**
- `POSTGRES_HOST`: warehouse
- `POSTGRES_PORT`: 5432
- `POSTGRES_DB`: qb_data
- `POSTGRES_USER`: root
- `POSTGRES_PASSWORD`: root

### Proceso de Rotación

- **QB Tokens**: Los refresh tokens duran 100 días. Renovar antes del vencimiento.
- **Responsable**: Administrador del proyecto
- **Método**: Actualizar directamente en Mage Secrets

## Pipelines Implementados

### qb_customers_backfill

Extrae datos de clientes de QuickBooks Online.

**Parámetros:**
- `fecha_inicio`: Fecha inicial en formato YYYY-MM-DD (UTC)
- `fecha_fin`: Fecha final en formato YYYY-MM-DD (UTC)

**Funcionalidad:**
- Query: `SELECT * FROM Customer`
- Filtro por MetaData.LastUpdatedTime
- Paginación automática (100 registros por página)
- Gestión de rate limits con pausas de 0.5 segundos

### qb_invoices_backfill

Extrae facturas de QuickBooks Online.

**Parámetros:**
- `fecha_inicio`: Fecha inicial en formato YYYY-MM-DD (UTC)
- `fecha_fin`: Fecha final en formato YYYY-MM-DD (UTC)

**Funcionalidad:**
- Query: `SELECT * FROM Invoice`
- Filtro por TxnDate o LastUpdatedTime
- Manejo de reintentos en errores de red
- Validación de datos antes de inserción

### qb_items_backfill

Extrae productos y servicios de QuickBooks Online.

**Parámetros:**
- `fecha_inicio`: Fecha inicial en formato YYYY-MM-DD (UTC)
- `fecha_fin`: Fecha final en formato YYYY-MM-DD (UTC)

**Funcionalidad:**
- Query: `SELECT * FROM Item`
- Filtro por MetaData.LastUpdatedTime
- Manejo específico de rate limits (429 errors)
- Backoff exponencial en reintentos

## Triggers One-Time

### Configuración

Cada pipeline se ejecuta mediante un trigger de una sola vez configurado en Mage.

**Configuración utilizada:**
- Fecha de ejecución: 12 de septiembre 2025, 14:35 UTC (11:35 América/Guayaquil)
- Runtime variables:
  - `fecha_inicio`: 2024-01-01
  - `fecha_fin`: 2025-12-31
- Frequency: `once`

### Política de Deshabilitación

Los triggers se deshabilitan automáticamente después de la ejecución exitosa. No se permite re-ejecución automática para evitar duplicación de datos.

## Esquema Raw

### Estructura de Tablas

Cada entidad tiene su tabla correspondiente en el esquema `raw`:

**raw.qb_customers**
**raw.qb_invoices**
**raw.qb_items**

### Campos Comunes

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | VARCHAR(50) | Clave primaria (ID de QuickBooks) |
| payload | JSONB | JSON completo de la respuesta API |
| ingested_at_utc | TIMESTAMP | Momento de inserción en UTC |
| extract_window_start_utc | TIMESTAMP | Inicio de ventana de extracción |
| extract_window_end_utc | TIMESTAMP | Fin de ventana de extracción |
| page_number | INTEGER | Número de página procesada |
| page_size | INTEGER | Tamaño de página utilizado |
| request_payload | JSONB | Metadatos de la request original |

### Índices

```sql
CREATE INDEX idx_qb_customers_ingested ON raw.qb_customers(ingested_at_utc);
CREATE INDEX idx_qb_invoices_ingested ON raw.qb_invoices(ingested_at_utc);
CREATE INDEX idx_qb_items_ingested ON raw.qb_items(ingested_at_utc);
```

### Idempotencia

Los pipelines implementan idempotencia mediante verificación de registros existentes antes de insertar. Re-ejecutar el mismo rango de fechas no genera duplicados.

**Verificación:**
```sql
SELECT id, COUNT(*) 
FROM raw.qb_customers 
GROUP BY id 
HAVING COUNT(*) > 1;
```

Debe devolver 0 filas.

## Validaciones y Volumetría

### Validaciones Automáticas

- Verificación de IDs no nulos
- Eliminación de duplicados por ID
- Validación de tipos de datos
- Verificación de JSON válido en payloads

### Métricas Registradas

Por cada ejecución se capturan:
- Número total de registros extraídos de la API
- Registros después del filtro de fechas
- Registros nuevos vs existentes (idempotencia)
- Duración total del proceso
- Errores y reintentos realizados

### Consultas de Verificación

```sql
-- Conteo por tabla
SELECT 
    'customers' as tabla, COUNT(*) as registros FROM raw.qb_customers
UNION ALL
SELECT 
    'invoices' as tabla, COUNT(*) as registros FROM raw.qb_invoices
UNION ALL
SELECT 
    'items' as tabla, COUNT(*) as registros FROM raw.qb_items;

-- Verificación de integridad
SELECT 
    COUNT(*) as total,
    COUNT(DISTINCT id) as unicos,
    COUNT(*) FILTER (WHERE id IS NULL) as nulos
FROM raw.qb_customers;
```

## Troubleshooting

### Problemas de Autenticación

**Error: Token expirado**
```
Solución: Verificar QB_REFRESH_TOKEN en Mage Secrets y renovar si es necesario
```

**Error: Credenciales inválidas**
```
Solución: Verificar QB_CLIENT_ID y QB_CLIENT_SECRET en Mage Secrets
```

### Problemas de API

**Error: 429 Too Many Requests**
```
Solución: Los pipelines manejan esto automáticamente con reintentos y pausas
```

**Error: Registros faltantes**
```
Solución: Verificar parámetros fecha_inicio/fecha_fin en el trigger
```

### Problemas de Base de Datos

**Error: Conexión a PostgreSQL**
```
Solución:
1. Verificar que el contenedor PostgreSQL esté corriendo
2. Verificar secrets POSTGRES_* en Mage
3. Confirmar comunicación por nombre de servicio 'warehouse'
```

**Error: Tabla no existe**
```
Solución: Ejecutar init_qb_schema.sql en PostgreSQL
```

### Problemas de Zonas Horarias

**Error: Fechas incorrectas en filtros**
```
Solución: Todos los parámetros de fecha deben estar en formato YYYY-MM-DD
Los timestamps internos se manejan automáticamente en UTC
```

## Runbook de Operación

### Re-ejecutar Pipeline Fallido

1. Identificar el pipeline fallido en Mage
2. Revisar logs para determinar la causa del error
3. Corregir el problema (secrets, conectividad, etc.)
4. Crear nuevo trigger one-time con los mismos parámetros
5. Ejecutar y monitorear hasta completar exitosamente

### Verificar Ejecución Exitosa

```sql
-- Verificar que no hay duplicados
SELECT 'qb_customers' as tabla, COUNT(*) - COUNT(DISTINCT id) as duplicados
FROM raw.qb_customers
UNION ALL
SELECT 'qb_invoices', COUNT(*) - COUNT(DISTINCT id) FROM raw.qb_invoices
UNION ALL  
SELECT 'qb_items', COUNT(*) - COUNT(DISTINCT id) FROM raw.qb_items;
```

### Añadir Nueva Ventana de Fechas

1. Crear nuevo trigger one-time en Mage
2. Configurar fecha_inicio y fecha_fin para el nuevo rango
3. Ejecutar pipeline
4. Verificar que los datos se insertan sin conflictos

### Reintentos y Reanudación

Los pipelines manejan automáticamente:
- Reintentos con backoff exponencial (hasta 3 intentos)
- Pausas en rate limits (basado en header Retry-After)
- Validación de datos antes de insertar

No se requiere intervención manual para casos normales de reintento.

## Evidencias

Las evidencias del proyecto se encuentran en la carpeta `/evid/` e incluyen:

- Configuración de Mage Secrets
- Triggers one-time ejecutados
- Tablas con datos en PostgreSQL
- Verificaciones de integridad e idempotencia
- Logs de ejecución de pipelines

## Checklist de Aceptación

- [x] Mage y Postgres se comunican por nombre de servicio
- [x] Todos los secretos están en Mage Secrets; no hay secretos expuestos
- [x] Pipelines acepta fecha_inicio y fecha_fin (UTC) y segmenta el rango
- [x] Trigger one-time configurado, ejecutado y deshabilitado
- [x] Esquema raw con payload completo y metadatos obligatorios
- [x] Idempotencia verificada: re-ejecución no genera duplicados
- [x] Paginación y rate limits manejados y documentados
- [x] Volumetría y validaciones registradas como evidencia
- [x] Runbook de reanudación y reintentos disponible

## Información del Proyecto

**Curso**: Data Mining  
Universidad San Francisco de Quito  
**Fecha**: 12 Septiembre 2025


FRANCISCO JESUS ALARCON AGUIRRE
