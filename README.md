# Product Value Dashboard with Shelf Snapshot

This is a Streamlit prototype with two pages:

- `Product Value Matrix`
- `Shelf Snapshot`

Both pages read from the same product table.

## Files

- `streamlit_app.py`: main Streamlit app
- `requirements.txt`: packages needed by Streamlit Cloud
- `data/product_data_sample.csv`: local sample data

## Data Source

The app can read data in three ways:

1. Google Sheets CSV URL from Streamlit Secrets
2. Uploaded CSV/XLSX file in the sidebar
3. Local sample file at `data/product_data_sample.csv`

For Streamlit Cloud, use this secret name:

```toml
GOOGLE_SHEET_CSV_URL = "your_google_sheet_csv_export_url"
```

## Required Columns

The product table should include:

- `Channel`
- `Brand`
- `Model Number`
- `URL of Image`
- `Pickup or not`
- `Sold by`
- `Was Price`
- `Price`
- `Capacity/mAh`
- `USB power (Max)`
- `Link`
- date columns such as `2026-07-06`

Date column rules:

- `Add` means the product entered the shelf.
- `Unavailable` means the product left the shelf.
- Blank means no status change.

## Product Value Matrix

This page shows the price-value scatter plot.

It supports:

- channel filter
- brand filter
- pickup filter
- availability on query date
- magnetic charging filter
- capacity filter
- USB power filter
- product image mode
- brand color mode

## Shelf Snapshot

This page summarizes one selected channel.

The top of the page shows three English insight cards first.

Then it shows:

- Total SKUs
- Available SKUs
- Pickup SKUs
- Pickup Coverage
- Unavailable SKUs
- Latest Tracking Date
- Brand Shelf Presence
- Pickup Coverage by brand
- Price Drop Signal
- New Entrants
- Data Quality Note

## How To Deploy

1. Create a new GitHub repository.
2. Upload these files and folders:
   - `streamlit_app.py`
   - `requirements.txt`
   - `README.md`
   - `data/product_data_sample.csv`
3. Create a new Streamlit Cloud app from that GitHub repository.
4. Add `GOOGLE_SHEET_CSV_URL` in Streamlit Secrets.
5. Redeploy the app.

