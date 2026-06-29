# UHC Transparency in Coverage â€” PresentaciÃ³n TÃ©cnica

> **Prueba tÃ©cnica: Data Engineer**
> Pipeline de extracciÃ³n, transformaciÃ³n y anÃ¡lisis de datos de transparencia sanitaria de UHC

---

## Resumen del Pipeline

![Pipeline Summary](charts/00_pipeline_summary.png)

---

## 1. Contexto: Â¿QuÃ© es UHC Transparency in Coverage?

El gobierno de EE.UU. (CMS) obliga a las aseguradoras de salud a publicar sus **tarifas negociadas** con proveedores mÃ©dicos en formato legible por mÃ¡quinas (Machine-Readable Files).

**UnitedHealthcare (UHC)** publica estos archivos en:
`https://transparency-in-coverage.uhc.com/`

### Estructura de datos (esquema CMS v2.0):

```mermaid
graph TD
    A["Index File<br/>(tabla de contenido)"] --> B["reporting_entity_name<br/>reporting_entity_type"]
    A --> C["reporting_structure"]
    C --> D["reporting_plans<br/>(plan_name, plan_id, plan_id_type)"]
    C --> E["in_network_files<br/>(URLs a archivos de tarifas)"]
    C --> F["allowed_amount_file<br/>(URLs a archivos de importes)"]
```

Cada empresa/empleador tiene un **index file** que apunta a archivos de tarifas que pueden pesar **varios gigabytes**.

---

## 2. El Reto TÃ©cnico

> [!WARNING]
> El sitio web de UHC NO es una pÃ¡gina estÃ¡tica. Es una **Single Page Application (SPA)** construida con JavaScript.

**Problemas encontrados:**
- No se puede hacer scraping HTML con BeautifulSoup â€” la pÃ¡gina renderiza contenido con JS
- No existe API pÃºblica documentada
- El servidor aplica **rate limiting** y devuelve errores 500 intermitentes
- Los archivos referenciados son enormes (multi-GB)

**SoluciÃ³n:** DescubrÃ­ que el sitio usa internamente una API REST:

```
GET https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/
```

Esta API devuelve un JSON con **86,514 blobs** (archivos disponibles), incluyendo nombre, URL de descarga y tamaÃ±o. De estos, filtrÃ© los `*_index.json` y tomÃ© los primeros **1,000**.

---

## 3. Arquitectura del Pipeline

```mermaid
graph TB
    subgraph "Paso 1: Discovery"
        A["API UHC /blobs/"] -->|"GET JSON"| B["86,514 blobs"]
        B -->|"Filtrar *_index.json"| C["1,000 index files"]
        C --> D["index_manifest.csv"]
    end

    subgraph "Paso 2: Download"
        D --> E["Streaming download<br/>+ 3 reintentos<br/>+ backoff exponencial"]
        E --> F["1,000 archivos JSON<br/>en data/raw/"]
        E --> G["download_log.csv"]
    end

    subgraph "Paso 3: Parse"
        F --> H["NormalizaciÃ³n JSON<br/>â†’ 4 tablas Parquet"]
        H --> I["index_files.parquet"]
        H --> J["plans.parquet"]
        H --> K["referenced_files.parquet"]
        H --> L["reporting_entities.parquet"]
    end

    subgraph "Paso 4: Insights"
        I --> M["AnÃ¡lisis + VisualizaciÃ³n"]
        J --> M
        K --> M
        M --> N["insights_summary.md<br/>+ 11 grÃ¡ficos PNG"]
    end

    style A fill:#E3F2FD,stroke:#1565C0
    style D fill:#E8F5E9,stroke:#2E7D32
    style F fill:#FFF3E0,stroke:#E65100
    style N fill:#F3E5F5,stroke:#6A1B9A
```

---

## 4. Paso a Paso: ExplicaciÃ³n Detallada

### Paso 1 â€” Discovery ([01_discover_index_files.py](file:///c:/Users/jlbahon.INDRA/Documents/GitHub/UNH-DE-CODE-TEST/src/01_discover_index_files.py))

**Â¿QuÃ© hace?** Consulta la API de UHC para obtener la lista completa de archivos disponibles y filtra los index files.

**Â¿Por quÃ© asÃ­?**
- El sitio es una SPA â†’ no funciona scraping HTML
- La API devuelve JSON estructurado â†’ mucho mÃ¡s fiable
- Filtramos por `*_index.json` porque la tarea pide especÃ­ficamente los archivos Ã­ndice
- Limitamos a 1,000 como indica la tarea

**CÃ³digo clave:**
```python
# Llamada directa a la API interna de UHC
response = requests.get("https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/",
                        timeout=120, headers={"Accept": "application/json"})
blobs = response.json().get("blobs", [])  # â†’ 86,514 blobs

# Filtrar solo index files
for blob in blobs:
    if blob["name"].endswith("_index.json"):
        # Guardar: file_name, download_url, file_size_bytes
```

**Resultado:** `data/processed/index_manifest.csv` con 1,000 filas.

---

### Paso 2 â€” Download ([02_download_index_files.py](file:///c:/Users/jlbahon.INDRA/Documents/GitHub/UNH-DE-CODE-TEST/src/02_download_index_files.py))

**Â¿QuÃ© hace?** Descarga los 1,000 archivos JSON del manifest de forma segura.

**Â¿Por quÃ© asÃ­?**
- **Streaming download** â†’ evita cargar archivos grandes en memoria
- **3 reintentos con backoff exponencial** (2s, 4s, 8s) â†’ maneja errores 500 del servidor
- **Size guard** â†’ omite archivos mayores a 512 MB para proteger disco local
- **Rate limiting** â†’ delay configurable entre descargas para respetar lÃ­mites del servidor
- **Idempotente** â†’ si un archivo ya existe, lo salta (permite re-ejecutar sin duplicar trabajo)
- **Barra de progreso** (tqdm) â†’ visibilidad en tiempo real

**CÃ³digo clave:**
```python
# Retry con backoff exponencial
for attempt in range(1, retries + 1):
    try:
        with requests.get(url, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=256*1024):
                f.write(chunk)
    except Exception:
        wait = BACKOFF_BASE ** attempt  # 2s, 4s, 8s
        time.sleep(wait)
```

**Resultado:** 1,000/1,000 archivos descargados (0 fallos). ~2.7 MB total.

![Download Status](charts/01_download_status.png)

---

### Paso 3 â€” Parse ([03_parse_index_files.py](file:///c:/Users/jlbahon.INDRA/Documents/GitHub/UNH-DE-CODE-TEST/src/03_parse_index_files.py))

**Â¿QuÃ© hace?** Normaliza los JSON anidados en 4 tablas planas almacenadas en Parquet.

**Â¿Por quÃ© asÃ­?**
- Los JSON tienen **estructura anidada** (reporting_structure â†’ plans â†’ files) â†’ necesitamos aplanar
- **Parquet** es columnar â†’ consultas analÃ­ticas rÃ¡pidas, compatible con Snowflake/Spark/Pandas
- **Modelo normalizado** â†’ evita redundancia, permite JOINs limpios
- **Parse separado de download** â†’ un fallo en descarga no bloquea anÃ¡lisis del resto

**Modelo de datos:**

```mermaid
erDiagram
    INDEX_FILES ||--o{ PLANS : "1:N"
    INDEX_FILES ||--|| REPORTING_ENTITIES : "1:1"
    PLANS ||--o{ REFERENCED_FILES : "1:N"

    INDEX_FILES {
        int index_file_id PK
        string file_name
        string reporting_entity_name
        string reporting_entity_type
        string version
    }
    PLANS {
        string plan_key PK
        int index_file_id FK
        string plan_name
        string plan_id
        string plan_id_type
        string plan_market_type
    }
    REFERENCED_FILES {
        string referenced_file_key PK
        string plan_key FK
        string file_type
        string location_url
    }
```

**Resultado:** 1,000 index files â†’ 1,833 planes â†’ 9,000 archivos referenciados. **100% parse rate.**

---

### Paso 4 â€” Insights ([04_generate_insights.py](file:///c:/Users/jlbahon.INDRA/Documents/GitHub/UNH-DE-CODE-TEST/src/04_generate_insights.py) + [05_advanced_insights.py](file:///c:/Users/jlbahon.INDRA/Documents/GitHub/UNH-DE-CODE-TEST/src/05_advanced_insights.py))

**Â¿QuÃ© hace?** Genera un reporte Markdown con mÃ©tricas clave y 11 grÃ¡ficos PNG con anÃ¡lisis visual profundo.

**Â¿Por quÃ© dos scripts?**
- `04` genera el reporte textual con tablas â†’ rÃ¡pido, ligero
- `05` genera visualizaciones con matplotlib/seaborn â†’ profundidad analÃ­tica para la entrevista

---

## 5. Insights del Datos

### Insight A: CentralizaciÃ³n Masiva de Datos

![URL Sharing Distribution](charts/10_url_sharing.png)

**Hallazgo:** Solo **385 URLs distintas** sirven **9,000 referencias**. Un solo archivo de tarifas es referenciado por hasta **873 archivos Ã­ndice**.

**Â¿QuÃ© significa?** UHC usa un **modelo hub-and-spoke**: un pequeÃ±o conjunto de archivos de tarifas negociadas es compartido por cientos de empleadores. La personalizaciÃ³n de tarifas a nivel de empleador es rara â€” la mayorÃ­a de empresas obtienen las mismas tarifas negociadas.

![Top Referenced URLs](charts/05_url_reuse.png)

---

### Insight B: ConcentraciÃ³n de Entidades

![Entity Distribution](charts/02_entity_distribution.png)

**Hallazgo:** **88.1%** de los archivos pertenecen a **United-HealthCare-Services-Inc**. Todas las entidades son **Third-Party Administrators (TPAs)**.

**Â¿QuÃ© significa?** UHC opera principalmente como administrador tercero (TPA). Oxford Health Plans (4.7%) y UMR (5.3%) son administradores secundarios, probablemente para segmentos regionales o especializados.

![Entity Plan Breakdown](charts/08_entity_plan_breakdown.png)

---

### Insight C: Portfolio de Redes de Seguros

![Network Types](charts/06_network_types.png)

**Hallazgo:** Las redes mÃ¡s populares son:
1. **OHPH ST** â€” 1,736 referencias (red de Optum Health para servicios estÃ¡ndar)
2. **OHPH Acupuncture/Massage/Naturopath** â€” 1,736 refs (medicina alternativa)
3. **OHPH Chiro** â€” 1,736 refs (quiroprÃ¡ctica)
4. **Choice Plus** â€” 1,135 refs (red PPO principal de UHC)
5. **Core** â€” 826 refs (red bÃ¡sica)

**Â¿QuÃ© significa?** Las redes OHPH (Optum Health) aparecen en casi todos los planes, lo que sugiere que los servicios de salud complementarios son **obligatorios** en la mayorÃ­a de planes UHC. Choice Plus es la red PPO mÃ¡s comÃºn.

---

### Insight D: Complejidad de Planes por Empleador

![Plans per Index](charts/03_plans_per_index.png)

**Hallazgo:**
- **51.7%** de empleadores tienen exactamente **1 plan** (plan Ãºnico)
- **48.3%** tienen **mÃºltiples planes** (hasta 10)
- Media: 1.83 planes por empleador

**Â¿QuÃ© significa?** La mayorÃ­a de empresas pequeÃ±as ofrecen un solo plan de salud. Las empresas mÃ¡s grandes ofrecen mÃºltiples opciones, lo que aumenta la complejidad del reporting de transparencia.

---

### Insight E: Tipos de Archivos Referenciados

![File Type Split](charts/04_file_type_pie.png)

**Hallazgo:** El **98.5%** de archivos referenciados son **in-network rates** vs solo **1.5%** de allowed amounts.

**Â¿QuÃ© significa?** Casi toda la data de transparencia se centra en las tarifas negociadas con proveedores dentro de la red. Los archivos de "allowed amounts" (para servicios fuera de red) son mucho menos comunes, lo que sugiere que UHC prioriza la cobertura dentro de red.

---

### Insight Adicional: DistribuciÃ³n de TamaÃ±os y Referencias por Ãndice

````carousel
![Referenced Files per Index](charts/07_refs_per_index.png)
<!-- slide -->
![File Size Distribution](charts/09_file_size_dist.png)
````

- **Media de 9 archivos referenciados** por index file
- Los index files son ligeros (2-3 KB media), pero referencian archivos de **gigabytes**
- Volumen total descargado: solo **2.7 MB** para 1,000 Ã­ndices

---

## 6. Calidad de Datos

| Check | Resultado |
|-------|-----------|
| Archivos descargados correctamente | âœ… 1,000/1,000 (100%) |
| Archivos parseados sin error | âœ… 1,000/1,000 (100%) |
| `reporting_entity_name` no nulo | âœ… 0 nulos |
| `plan_name` no nulo | âœ… 0 nulos |
| `plan_id` no nulo | âœ… 0 nulos |
| `location_url` no nulo | âœ… 0 nulos |
| VersiÃ³n del esquema | Todas las versiones presentes |

> [!TIP]
> No se detectaron problemas de calidad en los 1,000 archivos analizados. Esto indica que UHC mantiene un buen control de calidad en sus publicaciones de transparencia.

---

## 7. Decisiones de DiseÃ±o

| DecisiÃ³n | Alternativa | Por quÃ© elegÃ­ esta opciÃ³n |
|----------|-------------|---------------------------|
| API REST vs Scraping HTML | Selenium/Playwright | MÃ¡s rÃ¡pido, mÃ¡s fiable, sin dependencia de navegador |
| Streaming download | `json.load()` completo | Evita cargar archivos grandes en memoria |
| Retry + backoff exponencial | Retry simple | Respeta rate limits del servidor, evita ban |
| Parquet | CSV | Columnar, tipado, compresiÃ³n, compatible con Snowflake |
| Modelo normalizado | JSON plano | Evita redundancia, permite JOINs eficientes |
| Pipeline en 4 pasos | Script monolÃ­tico | Cada paso es independiente, recuperable, testeable |
| Download idempotente | Re-descargar siempre | Ahorra tiempo en re-ejecuciones |

---

## 8. ProductivizaciÃ³n

```mermaid
graph LR
    subgraph "OrquestaciÃ³n"
        A["Apache Airflow<br/>o Azure Data Factory"]
    end

    subgraph "Pipeline Diario"
        B["Discover"] --> C["Download"] --> D["Parse"] --> E["Load Snowflake"]
    end

    subgraph "MonitorizaciÃ³n"
        F["Alertas en fallos"]
        G["Data quality checks"]
        H["AnomalÃ­as de volumen"]
    end

    A --> B
    E --> F
    E --> G
    E --> H

    style A fill:#E3F2FD
    style E fill:#E8F5E9
    style F fill:#FFEBEE
```

**Mejoras para producciÃ³n:**
- **OrquestaciÃ³n:** Airflow/ADF con scheduling mensual (UHC actualiza datos cada mes)
- **Incremental:** Rastrear `last_updated_on` para solo descargar archivos nuevos
- **Storage:** Raw en S3/ADLS, curado en Snowflake con dbt
- **CI/CD:** GitHub Actions para tests y deploy
- **Monitoring:** Alertas en fallos de descarga, anomalÃ­as de parse rate, cambios de volumen
- **Seguridad:** Credenciales en secrets manager, cifrado at-rest

---

## 9. Stack TecnolÃ³gico

| Componente | TecnologÃ­a |
|------------|-----------|
| Lenguaje | Python 3.14 |
| HTTP | requests (streaming) |
| Procesamiento | pandas |
| Almacenamiento | Parquet (pyarrow) |
| VisualizaciÃ³n | matplotlib + seaborn |
| Base de datos (opcional) | Snowflake |
| Progreso | tqdm |
| Control de versiones | Git + GitHub |

---

## 10. CÃ³mo Ejecutar

```bash
# Setup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Pipeline completo
python src/01_discover_index_files.py --limit 1000    # ~15 seg
python src/02_download_index_files.py --limit 1000    # ~35 min
python src/03_parse_index_files.py                     # ~1 min
python src/04_generate_insights.py                     # ~30 seg
python src/05_advanced_insights.py                     # ~10 seg

# Opcional: cargar a Snowflake
python src/06_load_to_snowflake.py
```

---

## 11. Estructura del Repositorio

```
UNH-DE-CODE-TEST/
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ 01_discover_index_files.py   â†  API discovery
â”‚   â”œâ”€â”€ 02_download_index_files.py   â†  Streaming download + retry
â”‚   â”œâ”€â”€ 03_parse_index_files.py      â†  JSON â†’ 4 tablas Parquet
â”‚   â”œâ”€â”€ 04_generate_insights.py      â†  Reporte textual
â”‚   â”œâ”€â”€ 05_advanced_insights.py      â†  GrÃ¡ficos + insights profundos
â”‚   â”œâ”€â”€ 06_load_to_snowflake.py      â†  Carga opcional a Snowflake
â”‚   â””â”€â”€ utils/
â”‚       â”œâ”€â”€ __init__.py
â”‚       â””â”€â”€ io_utils.py
â”œâ”€â”€ sql/
â”‚   â”œâ”€â”€ create_tables.sql            â†  DDL Snowflake
â”‚   â””â”€â”€ insights.sql                 â†  Queries analÃ­ticas
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ raw/                         â† 1,000 JSON descargados
â”‚   â””â”€â”€ processed/                   â† Parquet + CSV de log
â”œâ”€â”€ reports/
â”‚   â”œâ”€â”€ insights_summary.md          â† Reporte principal
â”‚   â”œâ”€â”€ extended_insights.md         â† AnÃ¡lisis profundo
â”‚   â””â”€â”€ charts/                      â† 11 grÃ¡ficos PNG
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ config.example.env
â””â”€â”€ README.md
```

