# EDGAR Rate Limits : Current max request rate: 10 requests/second.
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd

# Retrieve JSON for Alphabet
goog_json_url = r"https://data.sec.gov/submissions/CIK0001652044.json"
driver = webdriver.Chrome()
driver.get(goog_json_url)
goog_large_json_string = driver.find_element(By.TAG_NAME, "pre").get_attribute("innerHTML")
driver.quit()
goog_json = json.loads(goog_large_json_string)

# Load JSON into a dataframe
recent_filings = goog_json["filings"]["recent"]
features = ["accessionNumber", "filingDate", "reportDate", "primaryDocument", "form"]
form_access_data = {feat: recent_filings[feat] for feat in features}
form_access_data.update({
    "fiscalYearEnd": goog_json["fiscalYearEnd"],
})
num_tickers = len(goog_json["tickers"])
form_access_data.update({
    f"ticker{i+1}": ticker for i, ticker in enumerate(goog_json["tickers"])
})

df = pd.DataFrame(form_access_data)

def create_filing_urls(df):
    """
    Returns a list of valid SEC urls
    """
    df = df.copy()
    df["accessionNumber"] = df["accessionNumber"].str.split("-")
    df["dir1"] = df["accessionNumber"].apply(lambda x: x[0]) + "/"
    df["dir2"] = df["accessionNumber"].apply("".join) + "/"

    df["url"] = (
        "https://www.sec.gov/ix?doc=/Archives/edgar/data/" +
        df["dir1"] +
        df["dir2"] +
        df["primaryDocument"]
    )

    tickers = [f"ticker{i+1}" for i in range(num_tickers)]
    return df[["url", "filingDate", "reportDate", "form", "fiscalYearEnd"] + tickers]

ten_k_forms = df.query(f"form.str.contains('10-K') or form.str.contains('10-Q')").reset_index(drop=True)
urls = create_filing_urls(ten_k_forms)

# make ticker common access
tickers = urls.loc[0,"ticker1":]

from pathlib import Path

for ticker in tickers:
    path = Path(f"data/{ticker}")
    path.mkdir(parents=True, exist_ok=True)

for ticker in tickers:
    urls.to_csv(f"data/{ticker}/urls.csv", index=True, header=True)