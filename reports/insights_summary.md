# UHC Transparency in Coverage — Insights Summary

> Generated at: 2026-06-26T11:53:14.293918+00:00

## 1. Ingestion Summary

| Metric | Value |
|--------|-------|
| Manifest rows processed | 1,000 |
| Total bytes downloaded | 2,838,976 (2.7 MB) |

**Download status breakdown:**

| status         |   count |
|:---------------|--------:|
| downloaded     |     996 |
| already_exists |       4 |

## 2. Parse Quality

| parse_status   |   count |
|:---------------|--------:|
| parsed         |    1000 |

## 3. Reporting Entities

- **Parsed index files:** 1,000
- **Distinct entity names:** 7

### Entity type distribution

| reporting_entity_type     |   count |
|:--------------------------|--------:|
| Third-Party Administrator |    1000 |

### Top 15 reporting entities (by index file count)

| reporting_entity_name              |   count |
|:-----------------------------------|--------:|
| United-HealthCare-Services-Inc     |     881 |
| UMR-Inc                            |      53 |
| Oxford-Health-Plans-LLC            |      47 |
| Surest                             |      15 |
| United-HealthCare-Services         |       2 |
| HealthSCOPE-Benefits-Inc           |       1 |
| UnitedHealthcare-Insurance-Company |       1 |

## 4. Plan Distribution

| Metric | Value |
|--------|-------|
| Total plan rows | 1,833 |
| Distinct plan names | 89 |
| Mean plans per index | 1.83 |
| Median plans per index | 1.00 |
| Max plans in one index | 10 |

### Plan market type distribution

| plan_market_type   |   count |
|:-------------------|--------:|
| group              |    1833 |

### Plan ID type distribution

| plan_id_type   |   count |
|:---------------|--------:|
| EIN            |    1833 |

## 5. Referenced Machine-Readable Files

| Metric | Value |
|--------|-------|
| Total referenced file rows | 9,000 |
| Distinct referenced URLs | 385 |
| Mean refs per index | 9.00 |

### File type split

| file_type      |   count |
|:---------------|--------:|
| in_network     |    8866 |
| allowed_amount |     134 |

### Top 15 most reused referenced URLs

| location_url                                                                                                                                                                                                           |   reference_count |   distinct_index_files |
|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------:|-----------------------:|
| https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/download/2026-06-01/2026-06-01_United-HealthCare-Services--Inc-_Third-Party-Administrator_OHPH-ST_30_in-network-rates.json.gz                                |              1651 |                    873 |
| https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/download/2026-06-01/2026-06-01_United-HealthCare-Services--Inc-_Third-Party-Administrator_OHPH-Acupuncture-Massage-Naturopath_31_in-network-rates.json.gz    |              1651 |                    873 |
| https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/download/2026-06-01/2026-06-01_United-HealthCare-Services--Inc-_Third-Party-Administrator_OHPH-Chiro_28_in-network-rates.json.gz                             |              1651 |                    873 |
| https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/download/2026-06-01/2026-06-01_United-HealthCare-Services--Inc-_Third-Party-Administrator_Choice-Plus_8_in-network-rates.json.gz                             |              1067 |                    659 |
| https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/download/2026-06-01/2026-06-01_United-HealthCare-Services--Inc-_Third-Party-Administrator_Core_579_in-network-rates.json.gz                                  |               757 |                    535 |
| https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/download/2026-06-01/2026-06-01_United-HealthCare-Services--Inc-_Third-Party-Administrator_Choice-EPO_561_in-network-rates.json.gz                            |               404 |                    252 |
| https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/download/2026-06-01/2026-06-01_United-HealthCare-Services--Inc-_Third-Party-Administrator_Core-EPO_578_in-network-rates.json.gz                              |               297 |                    201 |
| https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/download/2026-06-01/2026-06-01_United-HealthCare-Services--Inc-_Third-Party-Administrator_Optum-Health-Behavioral-Services--OHBS-_5_in-network-rates.json.gz |                85 |                     81 |
| https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/download/2026-06-01/2026-06-01_Oxford-Health-Plans-LLC_Third-Party-Administrator_OHPH-ST_30_in-network-rates.json.gz                                         |                84 |                     47 |
| https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/download/2026-06-01/2026-06-01_Oxford-Health-Plans-LLC_Third-Party-Administrator_CMC_CRS_MRRF_in-network-rates.json.gz                                       |                84 |                     47 |
| https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/download/2026-06-01/2026-06-01_Oxford-Health-Plans-LLC_Third-Party-Administrator_PPO---NDC_PPO-NDC_in-network-rates.json.gz                                  |                84 |                     47 |
| https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/download/2026-06-01/2026-06-01_Oxford-Health-Plans-LLC_Third-Party-Administrator_OHPH-Acupuncture-Massage-Naturopath_31_in-network-rates.json.gz             |                84 |                     47 |
| https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/download/2026-06-01/2026-06-01_Oxford-Health-Plans-LLC_Third-Party-Administrator_OHPH-Chiro_28_in-network-rates.json.gz                                      |                84 |                     47 |
| https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/download/2026-06-01/2026-06-01_Oxford-Health-Plans-LLC_Third-Party-Administrator_Core_579_in-network-rates.json.gz                                           |                69 |                     44 |
| https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/download/2026-06-01/2026-06-01_Oxford-Health-Plans-LLC_Third-Party-Administrator_Liberty-Network_25_in-network-rates.json.gz                                 |                69 |                     44 |

## 6. Data Quality Findings

No data quality issues detected.

## 7. Production Recommendations

- **Orchestration:** Schedule the pipeline with Apache Airflow or Azure Data Factory.
- **Storage:** Persist raw JSON in cloud object storage (S3/ADLS); curated Parquet in Snowflake.
- **Data Quality:** Add automated checks for missing fields, malformed URLs, duplicate plans, and row-count anomalies.
- **Incremental Loads:** Track `last_updated_on` to avoid re-downloading unchanged files.
- **Monitoring:** Set up alerts on download failures, parse errors, and volume anomalies.
- **CI/CD:** Version-control DDL, Python scripts, and dbt models. Deploy via GitHub Actions.
- **Security:** Rotate Snowflake credentials via secrets manager; encrypt data at rest.
