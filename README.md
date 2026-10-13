# Market Ledger — Bulk & Block Deals

No sample or fabricated trade data is included.

## Run locally
```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud
Upload `app.py` and `requirements.txt` to the repository root and set the main file path to `app.py`.

## Features
- Date-range filtering
- Company and symbol search
- Client disclosure history by period, stock, side, and quantity
- Company disclosure history
- CSV exports
- Optional best-effort NSE live request and CSV/XLSX upload for exchange reports

Client history includes only disclosures available in loaded reports, not a complete trading account history. NSE may block automated requests or change endpoints.
