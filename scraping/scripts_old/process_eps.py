import pandas as pd
import numpy as np
import json
import config

# make ticker common access (import reference)
ticker = config.ticker # primary ticker used as alias for all tickers
df = pd.read_csv(f"data/{ticker}/historical_eps.csv", index_col=0)
df = pd.concat((df, pd.read_csv(f"data/{ticker}/urls.csv", index_col=0)),
               axis=1)

tickers = df.loc[0, "ticker1":].to_list()

df["fiscalYearEnd"] = pd.to_datetime(df["fiscalYearEnd"].apply(lambda x: f"2000{x}"), format="%Y%m%d")

df["reportDate"] = pd.to_datetime(df["reportDate"], format=r"%Y-%m-%d")
df["fiscalYear"] =  -(-(df["reportDate"].dt.to_period("M").astype(int) - df["fiscalYearEnd"].dt.to_period("M").astype(int)) // 12) + 2000
df["quarter"] = 4 - (df["reportDate"].dt.to_period("M").astype(int) - df["fiscalYearEnd"].dt.to_period("M").astype(int))  % 4

def get_annual_eps_as_quarter_eps(df):
    df = df.copy()
    df["current_year_eps"] = df[["current_year_eps", "quarter"]].apply(lambda x: -x["current_year_eps"] if x["quarter"] != 4 else x["current_year_eps"], axis=1)
    df["prev_year_eps"] = df[["prev_year_eps", "quarter"]].apply(lambda x: -x["prev_year_eps"] if x["quarter"] != 4 else x["prev_year_eps"], axis=1)
    valid_years = df.groupby("fiscalYear").filter(lambda x: len(x) == 4)
    valid_years = valid_years.groupby("fiscalYear")[["current_year_eps", "prev_year_eps"]].apply(np.sum, axis=0).reset_index()
    valid_years["quarter"] = 4

    return valid_years

annual_eps = get_annual_eps_as_quarter_eps(df)

df = df.merge(annual_eps, on=["fiscalYear", "quarter"], how="left", suffixes=("", "_replace"))
df["current_year_eps"] = df.apply(lambda x: x["current_year_eps"] if np.isnan(x["current_year_eps_replace"]) else x["current_year_eps_replace"], axis=1)
df["prev_year_eps"] = df.apply(lambda x: x["prev_year_eps"] if np.isnan(x["prev_year_eps_replace"]) else x["prev_year_eps_replace"], axis=1)

df = df[["prev_year_eps", "current_year_eps", "filingDate", "reportDate", "form", "fiscalYear", "quarter"]]
current_fiscal_year = df["fiscalYear"].max()
full_year_indices = df.groupby("fiscalYear").filter(lambda x: len(x) == 4).index
curr_year_indices = df.query("fiscalYear == @current_fiscal_year").index

current_or_full_quarters = list(set(full_year_indices)|set(curr_year_indices))
df = df.iloc[current_or_full_quarters]
df[["prev_year_eps", "current_year_eps"]] = df[["prev_year_eps", "current_year_eps"]].apply(np.round, decimals=2)
df["filingDate"] = df["filingDate"].astype(str)
df["reportDate"] = df["reportDate"].astype(str)

df.columns = ["prev_year_eps", "current_year_eps", "filing_date", "report_date", "form", "fiscal_year", "quarter"]

for ticker in tickers:
    save_format = "csv"
    save_fp = f"data/{ticker}/processed_eps.{save_format}"
    if save_format == "csv":
        df["ticker"] = ticker
        df.to_csv(save_fp, index=False)
    elif save_format == "json":
        ticker_json = json.dumps({ticker: df.to_dict()})
        with open(f"data/{ticker}/processed_eps.json", "w") as f:
            f.write(ticker_json)
