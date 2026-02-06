import pandas as pd
import numpy as np
import json
import sys
from datetime import datetime, timedelta

# make ticker common access (import reference)
# ticker = sys.argv[1]
ticker = "AXP"
df = pd.read_csv(f"data/{ticker}/historical_eps.csv", index_col=0)
df = pd.concat((df, pd.read_csv(f"data/{ticker}/urls.csv", index_col=0)),
               axis=1)

df["fiscalYearEnd"] = pd.to_datetime(df["fiscalYearEnd"].apply(lambda x: f"2000{x}"), format="%Y%m%d")

df["reportDate"] = pd.to_datetime(df["reportDate"], format=r"%Y-%m-%d")
df["quarter"] = 4 * (df["form"] == "10-K").astype(int)
df["quarter"] =  4 - (df.index - df["quarter"].idxmax()) % 4
df["fiscalYear"] =  -(-(df["reportDate"].dt.to_period("M").astype(int) - (df["quarter"] == 4).idxmin() - df["fiscalYearEnd"].dt.to_period("M").astype(int)) // 12) + 2001

# TODO - prev_year_eps and curr_year_eps are currently being applied incorrectly.
# Ensure prev and current year eps are named correctly
if len(df) > 4:
    incorrect_order_count = (df["curr_year_eps"].iloc[4:].reset_index(drop=True) == df["prev_year_eps"].iloc[:-4].reset_index(drop=True)).sum()
    correct_order_count = (df["curr_year_eps"].iloc[:-4].reset_index(drop=True) == df["prev_year_eps"].iloc[4:].reset_index(drop=True)).sum()

    if incorrect_order_count < correct_order_count:
        df = df.rename(columns={"curr_year_eps":"prev_year_eps", "prev_year_eps":"curr_year_eps"})

df["prev_year_eps"] = None

split_dates = df.query("split_date.notna()")[["split_date", "stock_ratio_given", "stock_ratio_taken"]].to_numpy()
df["reportDate"] = df["reportDate"].astype(str)

for split_date, given, taken in split_dates:
    df["curr_year_eps"] = df[["reportDate", "curr_year_eps", "split_date"]].apply(
        lambda x: x["curr_year_eps"] * taken / given if x["reportDate"] <= split_date 
        else x["curr_year_eps"],
        axis=1
    )

def get_annual_eps_as_quarter_eps(df):
    df = df.copy()
    # print(df)
    df["curr_year_eps"] = df[["curr_year_eps", "quarter"]].apply(lambda x: -x["curr_year_eps"] if x["quarter"] != 4 else x["curr_year_eps"], axis=1)
    print(df)
    print("x x x")
    valid_years = (
        df
            .groupby("fiscalYear")
            .filter(lambda x: len(x) == 4 and not any(x["curr_year_eps"].isna()))
            .groupby("fiscalYear")
            [["curr_year_eps"]]
            .apply(np.sum, axis=0)
            .reset_index()
    )

    valid_years["quarter"] = 4
    print(valid_years)
    return valid_years

annual_eps = get_annual_eps_as_quarter_eps(df)

df = df.merge(annual_eps, on=["fiscalYear", "quarter"], how="left", suffixes=("", "_replace"))
df["curr_year_eps"] = df.apply(lambda x: x["curr_year_eps"] if np.isnan(x["curr_year_eps_replace"]) else x["curr_year_eps_replace"], axis=1)

valid_years = set(annual_eps["fiscalYear"].to_numpy())
df["curr_year_eps"] = df[["curr_year_eps", "fiscalYear"]].apply(lambda x: None if x["fiscalYear"] not in valid_years else x["curr_year_eps"], axis=1)

if len(df) > 4:
    df.loc[-4:, "prev_year_eps"] = df.loc[4:, "curr_year_eps"].reset_index(drop=True)

extraneous_columns = [
    "url",
    "curr_year_eps_replace",
]
df = df.drop(columns=extraneous_columns)
t = df.copy()

current_fiscal_year = df["fiscalYear"].max()
full_year_indices = df.groupby("fiscalYear").filter(lambda x: len(x) == 4).index
curr_year_indices = df.query("fiscalYear == @current_fiscal_year").index

current_or_full_quarters = list(set(full_year_indices)|set(curr_year_indices))
df = df.iloc[current_or_full_quarters]

df["filingDate"] = df["filingDate"].astype(str)
df["reportDate"] = df["reportDate"].astype(str)
df = df.drop(
    columns=[
        "stock_ratio_given",
        "stock_ratio_taken",
        "split_date",
        "fiscalYearEnd",
    ]
)

df = df.rename(columns={
    "filingDate": "filing_date",
    "reportDate": "report_date",
    "fiscalYear": "fiscal_year",
})

# print(df)

save_format = "csv"
save_fp = f"data/{ticker}/processed_eps.{save_format}"
if save_format == "csv":
    df["ticker"] = ticker
    df.to_csv(save_fp, index=False)
elif save_format == "json":
    ticker_json = json.dumps({ticker: df.to_dict()})
    with open(f"data/{ticker}/processed_eps.json", "w") as f:
        f.write(ticker_json)
