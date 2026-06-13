import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import sys

BASE_URL = "https://merolagani.com/Floorsheet.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/137 Safari/537.36"
}


class MerolaganiScraper:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    # =========================
    # FETCH SINGLE PAGE
    # =========================
    def fetch_page(self, page=1):
        try:
            url = f"{BASE_URL}?page={page}"
            r = self.session.get(url, timeout=30)

            if r.status_code != 200:
                print(f"[ERROR] Status: {r.status_code}")
                return []

            soup = BeautifulSoup(r.text, "lxml")

            rows = soup.select("table tbody tr")

            data = []

            for row in rows:
                cols = row.find_all("td")

                if len(cols) < 8:
                    continue

                try:
                    record = {
                        "Contract": cols[1].get_text(strip=True),
                        "Symbol": cols[2].get_text(strip=True),
                        "Buyer": cols[3].get_text(strip=True),
                        "Seller": cols[4].get_text(strip=True),
                        "Quantity": cols[5].get_text(strip=True).replace(",", ""),
                        "Rate": cols[6].get_text(strip=True).replace(",", ""),
                        "Amount": cols[7].get_text(strip=True).replace(",", "")
                    }
                    data.append(record)

                except:
                    continue

            return data

        except Exception as e:
            print("[ERROR]", e)
            return []

    # =========================
    # FETCH ALL PAGES
    # =========================
    def fetch_all(self, pages=3, delay=1):
        all_data = []

        for page in range(1, pages + 1):
            print(f"Fetching page {page}...")
            data = self.fetch_page(page)

            if not data:
                break

            all_data.extend(data)
            time.sleep(delay)

        return all_data

    # =========================
    # CLEAN DUPLICATES
    # =========================
    def clean_data(self, data):
        seen = set()
        output = []

        for row in data:
            key = (row["Contract"], row["Symbol"])

            if key not in seen:
                seen.add(key)
                output.append(row)

        return output

    # =========================
    # FILTER DATA
    # =========================
    def filter_data(self, data, symbol=None, broker=None):

        result = []

        for row in data:

            if symbol:
                if symbol.lower() not in row["Symbol"].lower():
                    continue

            if broker:
                if broker not in (row["Buyer"], row["Seller"]):
                    continue

            result.append(row)

        return result

    # =========================
    # BROKER ANALYSIS (FIXED)
    # =========================
    def broker_summary(self, data):

        buy_qty = {}
        sell_qty = {}

        for row in data:

            try:
                qty = int(float(row["Quantity"]))
            except:
                continue

            buyer = row["Buyer"]
            seller = row["Seller"]

            buy_qty[buyer] = buy_qty.get(buyer, 0) + qty
            sell_qty[seller] = sell_qty.get(seller, 0) + qty

        summary = []

        brokers = set(list(buy_qty.keys()) + list(sell_qty.keys()))

        for b in brokers:
            buy = buy_qty.get(b, 0)
            sell = sell_qty.get(b, 0)

            summary.append({
                "Broker": b,
                "BuyQty": buy,
                "SellQty": sell,
                "Net": buy - sell
            })

        df = pd.DataFrame(summary)

        if df.empty:
            return df

        return df.sort_values("Net", ascending=False)

    # =========================
    # SAVE DATA
    # =========================
    def save(self, data, name):

        df = pd.DataFrame(data)

        csv_file = f"{name}.csv"
        xlsx_file = f"{name}.xlsx"

        df.to_csv(csv_file, index=False)
        df.to_excel(xlsx_file, index=False)

        print(f"[✔] CSV saved: {csv_file}")
        print(f"[✔] Excel saved: {xlsx_file}")
        print(f"Rows: {len(df)}")


# =========================
# MAIN MENU
# =========================
def main():

    scraper = MerolaganiScraper()
    data_cache = None

    while True:

        print("\n===== MEROLAGANI FLOORSHEET =====")
        print("1. Fetch Data")
        print("2. Fetch + Filter")
        print("3. Broker Analysis")
        print("4. Exit")

        choice = input("Enter choice: ")

        # ======================
        # FETCH
        # ======================
        if choice == "1":

            data_cache = scraper.fetch_all(pages=3)
            data_cache = scraper.clean_data(data_cache)

            scraper.save(data_cache, "floorsheet")

            print("[✔] Data cached")

        # ======================
        # FILTER
        # ======================
        elif choice == "2":

            if not data_cache:
                print("[!] First run option 1")
                continue

            symbol = input("Enter symbol (blank=all): ").strip()
            broker = input("Enter broker (blank=all): ").strip()

            df = pd.DataFrame(data_cache)

            if symbol:
                df = df[df["Symbol"].str.contains(symbol, case=False)]

            if broker:
                df = df[
                    (df["Buyer"] == broker) |
                    (df["Seller"] == broker)
                ]

            scraper.save(df.to_dict("records"), "filtered")

            print("Filtered rows:", len(df))

        # ======================
        # BROKER ANALYSIS
        # ======================
        elif choice == "3":

            if not data_cache:
                print("[!] Run option 1 first")
                continue

            symbol = input("Symbol (e.g. VLBS): ").strip()

            df = pd.DataFrame(data_cache)

            if symbol:
                df = df[df["Symbol"].str.contains(symbol, case=False)]

            summary = scraper.broker_summary(df.to_dict("records"))

            print(summary.head(10))

        # ======================
        # EXIT
        # ======================
        elif choice == "4":
            sys.exit()

        else:
            print("Invalid choice!")


if __name__ == "__main__":
    main()