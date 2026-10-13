import re
from datetime import date, timedelta
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title='Market Ledger', page_icon='↗', layout='wide')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
.stApp{background:#f6f5ef;color:#172e27}.block-container{padding-top:1.5rem;max-width:1400px}
h1{font-family:'Playfair Display',serif;color:#172e27;letter-spacing:-.04em}
[data-testid="stSidebar"]{background:#eaece4;border-right:1px solid #dfe3da}
[data-testid="stMetric"]{background:white;border:1px solid #dfe3da;padding:14px;border-radius:10px}
@media(max-width:700px){.block-container{padding:.8rem .6rem 2rem}}
</style>''', unsafe_allow_html=True)
st.caption('MARKET INTELLIGENCE · INDIA')
st.title('Market Ledger')
st.write('Bulk & block deal research, searchable company records, and disclosed client trade history.')
st.info('No sample deals are included. Data appears only after you upload an exchange report or a live request succeeds.')

def norm(s): return re.sub(r'[^a-z0-9]+',' ',str(s).lower()).strip()
ALIASES={
 'date':['date','trade date','deal date','transaction date'],
 'stock':['stock','company','company name','security','symbol','scrip','name'],
 'client':['client','client name','investor','entity'],
 'side':['side','buy sell','buy/sell','transaction type','deal type'],
 'quantity':['quantity','qty','shares','traded quantity','no of shares'],
 'price':['price','trade price','deal price','avg price'],
 'exchange':['exchange','market']}
def normalize(raw):
 if raw is None or raw.empty: return pd.DataFrame()
 df=raw.copy(); lookup={norm(c):c for c in df.columns}; ren={}
 for target, aliases in ALIASES.items():
  for alias in aliases:
   if norm(alias) in lookup: ren[lookup[norm(alias)]]=target; break
 df=df.rename(columns=ren)
 if 'date' in df: df['date']=pd.to_datetime(df['date'],errors='coerce',dayfirst=True).dt.date
 if 'quantity' in df: df['quantity']=pd.to_numeric(df['quantity'].astype(str).str.replace(',','',regex=False),errors='coerce')
 if 'price' in df: df['price']=pd.to_numeric(df['price'].astype(str).str.replace(',','',regex=False),errors='coerce')
 for c in ['stock','client','side','exchange']:
  if c in df: df[c]=df[c].astype('string').str.strip()
 if 'stock' in df: df['stock']=df['stock'].fillna('').str.upper()
 if 'side' in df: df['side']=df['side'].str.upper().replace({'PURCHASE':'BUY','BOUGHT':'BUY','SOLD':'SELL'})
 if 'quantity' in df and 'price' in df: df['value']=df['quantity']*df['price']
 return df
def fetch_nse(start,end):
 s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 Chrome/126 Safari/537.36','Accept':'application/json,text/plain,*/*','Referer':'https://www.nseindia.com/report-detail/display-bulk-and-block-deals'})
 try:
  s.get('https://www.nseindia.com',timeout=10)
  r=s.get('https://www.nseindia.com/api/historical/bulk-deals',params={'from':start.strftime('%d-%m-%Y'),'to':end.strftime('%d-%m-%Y')},timeout=20); r.raise_for_status()
  p=r.json(); rows=p.get('data',[]) if isinstance(p,dict) else p
  return pd.DataFrame(rows),None
 except Exception as e: return pd.DataFrame(),f'NSE live fetch failed ({type(e).__name__}). NSE may block automated requests or change its endpoint. Upload an official report instead.'

with st.sidebar:
 st.subheader('Data source'); source=st.radio('Choose source',['Upload exchange report','Try live NSE fetch'])
 today=date.today(); start=st.date_input('From date',today-timedelta(days=30),max_value=today); end=st.date_input('To date',today,max_value=today)
 st.caption('Client history only covers public disclosures in the loaded data.')
data=pd.DataFrame(); error=None; source_name=''
if start>end: st.error('From date must be on or before To date.'); st.stop()
if source=='Upload exchange report':
 file=st.file_uploader('Upload official NSE/BSE report',type=['csv','xlsx','xls'])
 if file:
  try:
   raw=pd.read_csv(file) if file.name.lower().endswith('.csv') else pd.read_excel(file); data=normalize(raw); source_name=file.name
  except Exception as e: error=f'Could not read file: {e}'
else:
 st.warning('Live fetching is best-effort. BSE reports can be uploaded using the upload option.')
 if st.button('Fetch NSE deals',type='primary'):
  with st.spinner('Requesting NSE report...'):
   raw,error=fetch_nse(start,end)
   if not raw.empty: data=normalize(raw); source_name='NSE live request'
if error: st.warning(error)
if not data.empty:
 missing=[c for c in ['date','stock','client','quantity'] if c not in data.columns]
 if missing: st.error('Could not identify required columns: '+', '.join(missing)+'. Expected date, company/stock/symbol, client, and quantity.'); st.stop()
 data=data[data.date.notna()]; data=data[(data.date>=start)&(data.date<=end)].copy()
 if 'side' not in data: data['side']='—'
 if 'exchange' not in data: data['exchange']='—'
 if 'value' not in data and 'price' in data: data['value']=data.price*data.quantity
 st.caption('DATA SOURCE · '+source_name)
 c1,c2,c3=st.columns(3); c1.metric('Disclosed records',f'{len(data):,}'); q=data.quantity.sum(); c2.metric('Disclosed quantity',f'{q:,.0f}' if pd.notna(q) else '—'); c3.metric('Companies',f'{data.stock.nunique():,}')
 a,b,c=st.columns([1.2,1.2,1])
 with a: company_q=st.text_input('Search company / symbol',placeholder='Company or ticker')
 with b: client_q=st.text_input('Search client name',placeholder='Client / investor')
 with c: side_q=st.selectbox('Side',['All']+sorted(data.side.dropna().astype(str).unique().tolist()))
 filtered=data.copy()
 if company_q.strip(): filtered=filtered[filtered.stock.astype(str).str.contains(company_q.strip(),case=False,na=False)]
 if client_q.strip(): filtered=filtered[filtered.client.astype(str).str.contains(client_q.strip(),case=False,na=False)]
 if side_q!='All': filtered=filtered[filtered.side.astype(str)==side_q]
 tabs=st.tabs(['All trades','Client history','Company history'])
 show=[x for x in ['date','exchange','stock','client','side','quantity','price','value'] if x in filtered]
 with tabs[0]:
  st.dataframe(filtered[show].sort_values('date',ascending=False),use_container_width=True,hide_index=True)
  st.download_button('Export filtered trades CSV',filtered[show].to_csv(index=False).encode(),'filtered_trades.csv','text/csv')
 with tabs[1]:
  clients=sorted(data.client.dropna().astype(str).unique().tolist()); chosen=st.selectbox('Choose client',['']+clients)
  if chosen:
   hist=data[data.client.astype(str).str.casefold()==chosen.casefold()].copy(); hist=hist[(hist.date>=start)&(hist.date<=end)]
   if company_q.strip(): hist=hist[hist.stock.astype(str).str.contains(company_q.strip(),case=False,na=False)]
   if side_q!='All': hist=hist[hist.side.astype(str)==side_q]
   cols=[x for x in ['date','stock','side','quantity','price','value','exchange'] if x in hist]
   st.write(f'{len(hist)} disclosed records for {chosen} in the selected period.')
   st.dataframe(hist[cols].sort_values('date',ascending=False),use_container_width=True,hide_index=True)
   st.subheader('Client activity by stock'); st.dataframe(hist.groupby('stock',dropna=False).agg(records=('stock','size'),total_quantity=('quantity','sum')).reset_index().sort_values('total_quantity',ascending=False),use_container_width=True,hide_index=True)
   st.download_button('Export client history CSV',hist[cols].to_csv(index=False).encode(),'client_history.csv','text/csv')
  else: st.info('Select a client to see each disclosed trade, stock, date, side, and quantity.')
 with tabs[2]:
  companies=sorted(data.stock.dropna().astype(str).unique().tolist()); chosen_stock=st.selectbox('Choose company',['']+companies)
  if chosen_stock:
   hist=data[data.stock.astype(str).str.casefold()==chosen_stock.casefold()].copy(); cols=[x for x in ['date','client','side','quantity','price','value','exchange'] if x in hist]
   st.dataframe(hist[cols].sort_values('date',ascending=False),use_container_width=True,hide_index=True)
   st.download_button('Export company history CSV',hist[cols].to_csv(index=False).encode(),'company_history.csv','text/csv')
else:
 st.subheader('Start with an official report'); st.write('Upload a CSV/XLSX exchange report or try the live NSE request. No example deals or invented metrics are loaded.')
 with st.expander('Expected columns'): st.write('Date, company/stock/symbol, client, quantity, and optionally side, price, and exchange. If report headers differ, column mapping may need adjustment.')
st.divider(); st.caption("Public disclosures only. This is not a client's complete account history; repeated names or quantities do not prove connected ownership.")
