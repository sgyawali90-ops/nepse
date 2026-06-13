import requests
import pandas as pd
from bs4 import BeautifulSoup
import streamlit as st
import time
import re

BASE_URL = "https://merolagani.com/Floorsheet.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# =========================
# SCRAPER CORE
# =========================
class MerolaganiScraper:

    def fetch_page(self, page=1):
        try:
            url = f"{BASE_URL}?page={page}"
            r = requests.get(url, headers=HEADERS, timeout=20)

            soup = BeautifulSoup(r.text, "lxml")
            rows = soup.select("table tbody tr")

            data = []

            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 8:
                    continue

                data.append({
                    "Contract": cols[1].text.strip(),
                    "Symbol": cols[2].text.strip(),
                    "Buyer": cols[3].text.strip(),
                    "Seller": cols[4].text.strip(),
                    "Quantity": cols[5].text.replace(",", "").strip(),
                    "Rate": cols[6].text.replace(",", "").strip(),
                    "Amount": cols[7].text.replace(",", "").strip()
                })

            return data

        except:
            return []

    def fetch_all(self, pages=3):
        all_data = []

        for i in range(1, pages + 1):
            data = self.fetch_page(i)
            if not data:
                break
            all_data.extend(data)
            time.sleep(0.5)

        return pd.DataFrame(all_data)

# =========================
# FILTER FIXED
# =========================
def filter_data(df, symbol, broker):

    if symbol:
        df = df[df["Symbol"].str.contains(symbol, case=False)]

    if broker:
        df = df[
            df["Buyer"].astype(str).str.contains(broker, na=False) |
            df["Seller"].astype(str).str.contains(broker, na=False)
        ]

    return df

# =========================
# BROKER ANALYSIS
# =========================
def broker_analysis(df):

    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")

    buy = df.groupby("Buyer")["Quantity"].sum().reset_index()
    sell = df.groupby("Seller")["Quantity"].sum().reset_index()

    buy.columns = ["Broker", "BuyQty"]
    sell.columns = ["Broker", "SellQty"]

    merged = pd.merge(buy, sell, on="Broker", how="outer").fillna(0)

    merged["Net"] = merged["BuyQty"] - merged["SellQty"]

    return merged.sort_values("Net", ascending=False)

# =========================
# STREAMLIT UI
# =========================
st.set_page_config(page_title="NEPSE Floorsheet Pro", layout="wide")

st.title("📊 NEPSE Floorsheet Pro Dashboard")

scraper = MerolaganiScraper()

# SESSION CACHE
if "data" not in st.session_state:
    st.session_state.data = scraper.fetch_all(pages=3)

# =========================
# SIDEBAR CONTROLS
# =========================
st.sidebar.header("Filters")

symbol = st.sidebar.text_input("Symbol (e.g. ADBL)")
broker = st.sidebar.text_input("Broker (e.g. 45)")

if st.sidebar.button("🔄 Refresh Data"):
    st.session_state.data = scraper.fetch_all(pages=3)
    st.success("Data refreshed!")

df = st.session_state.data

# =========================
# FILTER
# =========================
filtered = filter_data(df, symbol, broker)

# =========================
# TABS
# =========================
tab1, tab2 = st.tabs(["📋 Floorsheet", "📈 Broker Analysis"])

with tab1:
    st.subheader("Floorsheet Data")
    st.write(f"Rows: {len(filtered)}")
    st.dataframe(filtered, use_container_width=True)

    st.download_button(
        "⬇ Download CSV",
        filtered.to_csv(index=False),
        "floorsheet.csv",
        "text/csv"
    )

with tab2:
    st.subheader("Broker Analysis")

    if len(filtered) > 0:
        result = broker_analysis(filtered)

        st.dataframe(result, use_container_width=True)

        st.bar_chart(result.set_index("Broker")["Net"])
    else:
        st.warning("No data for analysis")