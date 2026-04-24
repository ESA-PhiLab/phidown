# Phidown Command Patterns

## CLI quick checks
```bash
phidown --help
phidown --version
```

## Download by exact product name
```bash
phidown --name "S1A_IW_GRDH_1SDV_20141031T161924_20141031T161949_003076_003856_634E.SAFE" -o "./data"
```

## Download by S3 path
```bash
phidown --s3path "/eodata/Sentinel-1/SAR/IW_GRDH_1S/2024/05/03/..." -o "./data"
```

## Reset credential config
```bash
phidown --name "<PRODUCT_NAME>" -o "./data" --reset
```

## List products over AOI and dates
```bash
phidown list --collection "SENTINEL-1" --product-type "GRD" --bbox -5 40 5 45 --start-date "2024-01-01T00:00:00" --end-date "2024-01-31T23:59:59" --format "csv" --save "./outputs/products.csv"
```

## Burst coverage analysis over AOI and dates
```bash
phidown --burst-coverage --aoi-wkt "POLYGON((10 45, 12 45, 12 46, 10 46, 10 45))" --start-date "2024-08-02T00:00:00" --end-date "2024-08-20T23:59:59" --polarisation "VV" --orbit-direction "DESCENDING" --preferred-subswath "IW1,IW2,IW3" --format "json" --save "./outputs/burst_coverage.json"
```

## Python search and inspect
```python
from phidown.search import CopernicusDataSearcher

searcher = CopernicusDataSearcher()
searcher.query_by_filter(
    collection_name="SENTINEL-1",
    product_type="SLC",
    start_date="2025-01-01T00:00:00",
    end_date="2025-01-31T23:59:59",
    top=50,
)

df = searcher.execute_query()
print(f"results={len(df)}")
print(df[["Name", "S3Path"]].head(10))
```

## Python burst mode search
```python
from phidown.search import CopernicusDataSearcher

searcher = CopernicusDataSearcher()
searcher.query_by_filter(
    burst_mode=True,
    swath_identifier="IW2",
    polarisation_channels="VV",
    orbit_direction="DESCENDING",
    start_date="2025-01-01T00:00:00",
    end_date="2025-01-15T00:00:00",
    top=20,
    count=True,
)

df = searcher.execute_query()
print(f"bursts={len(df)} total={searcher.num_results}")
```
