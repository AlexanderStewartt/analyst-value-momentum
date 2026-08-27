import pandas as pd


def main():

    # Load historical S&P 500 membership data
    df = pd.read_csv("data/sp500_ticker_start_end.csv")

    # Clean column names
    df.columns = df.columns.str.strip().str.lower()

    # Convert dates
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")

    # Current members have blank end dates
    df["end_date"] = df["end_date"].fillna(pd.Timestamp("2099-12-31"))

    # Keep companies that were in the S&P 500 at any point from 2005-2025
    df = df[
        (df["start_date"] <= pd.Timestamp("2025-12-31")) &
        (df["end_date"] >= pd.Timestamp("2005-01-01"))
    ]

    # Get unique tickers
    tickers = sorted(df["ticker"].dropna().str.strip().str.upper().unique())

    print("Number of unique tickers:", len(tickers))
    print("\nTickers:\n")

    # Print in copy/paste format
    print(" ".join(tickers))


if __name__ == "__main__":
    main()