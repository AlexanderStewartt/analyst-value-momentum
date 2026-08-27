import pandas as pd


CRSP_FILE = "data/crsp_sp500_daily_2005_2025.csv"
SP500_FILE = "data/sp500_ticker_start_end.csv"

OUTPUT_FILE = "data/weekly_crsp_panel.csv"


def load_crsp(file_path):
    """
    Load the large CRSP daily dataset.
    """

    df = pd.read_csv(file_path)

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )

    df["dlycaldt"] = pd.to_datetime(
        df["dlycaldt"],
        errors="coerce"
    )

    df["ticker"] = (
        df["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["permno"] = pd.to_numeric(
        df["permno"],
        errors="coerce"
    )

    df["dlyprc"] = pd.to_numeric(
        df["dlyprc"],
        errors="coerce"
    )

    df["dlycap"] = pd.to_numeric(
        df["dlycap"],
        errors="coerce"
    )

    df["dlyret"] = pd.to_numeric(
        df["dlyret"],
        errors="coerce"
    )

    df["sprtrn"] = pd.to_numeric(
        df["sprtrn"],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "permno",
            "dlycaldt"
        ]
    )

    return df


def load_sp500_membership(file_path):
    """
    Load historical S&P 500 membership intervals.
    """

    df = pd.read_csv(file_path)

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )

    df["ticker"] = (
        df["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["start_date"] = pd.to_datetime(
        df["start_date"],
        errors="coerce"
    )

    df["end_date"] = pd.to_datetime(
        df["end_date"],
        errors="coerce"
    )

    # Blank end date = still active
    df["end_date"] = df["end_date"].fillna(
        pd.Timestamp("2099-12-31")
    )

    return df


def calculate_returns(crsp):
    """
    Calculate:

    prior_5d_return:
        compounded stock return over the previous
        five trading days including the signal date

    next_5d_return:
        compounded stock return over the NEXT
        five trading days

    next_5d_market_return:
        S&P 500 return over those same next
        five trading days

    next_5d_excess_return:
        stock return minus S&P 500 return
    """

    crsp = crsp.sort_values(
        ["permno", "dlycaldt"]
    ).copy()

    # -----------------------------------
    # Prior five-day stock return
    # -----------------------------------

    crsp["prior_5d_return"] = (
        crsp.groupby("permno")["dlyret"]
        .transform(
            lambda x:
                (1 + x)
                .rolling(5)
                .apply(
                    lambda r: r.prod() - 1,
                    raw=True
                )
        )
    )

    # -----------------------------------
    # Next five-day stock return
    # -----------------------------------

    crsp["next_5d_return"] = (
        crsp.groupby("permno")["dlyret"]
        .transform(
            lambda x:
                (1 + x)
                .rolling(5)
                .apply(
                    lambda r: r.prod() - 1,
                    raw=True
                )
                .shift(-5)
        )
    )

    # -----------------------------------
    # Next five-day S&P 500 return
    # -----------------------------------

    crsp["next_5d_market_return"] = (
        crsp.groupby("permno")["sprtrn"]
        .transform(
            lambda x:
                (1 + x)
                .rolling(5)
                .apply(
                    lambda r: r.prod() - 1,
                    raw=True
                )
                .shift(-5)
        )
    )

    # -----------------------------------
    # Market-adjusted return
    # -----------------------------------

    crsp["next_5d_excess_return"] = (
        crsp["next_5d_return"]
        -
        crsp["next_5d_market_return"]
    )

    return crsp


def create_weekly_signals(crsp):
    """
    Keep only the final trading day of each week
    for every security.
    """

    crsp = crsp.copy()

    crsp["week"] = (
        crsp["dlycaldt"]
        .dt.to_period("W-FRI")
    )

    weekly = (
        crsp
        .sort_values(["permno", "dlycaldt"])
        .groupby(["permno", "week"])
        .tail(1)
        .copy()
    )

    weekly = weekly.rename(
        columns={
            "dlycaldt": "signal_date"
        }
    )

    return weekly


def filter_to_historical_sp500(
    weekly,
    membership
):
    """
    Keep an observation only if that ticker was actually
    in the S&P 500 on the weekly signal date.
    """

    merged = weekly.merge(
        membership,
        on="ticker",
        how="inner"
    )

    valid = merged[
        (merged["signal_date"] >= merged["start_date"])
        &
        (merged["signal_date"] <= merged["end_date"])
    ].copy()

    # Prevent accidental duplicates from overlapping
    # membership records.
    valid = valid.drop_duplicates(
        subset=["permno", "signal_date"]
    )

    return valid


def inspect_panel(panel):
    """
    Basic diagnostics.
    """

    print("\n================================")
    print("WEEKLY CRSP PANEL")
    print("================================")

    print("\nRows:")
    print(len(panel))

    print("\nUnique PERMNOs:")
    print(panel["permno"].nunique())

    print("\nDate range:")
    print(
        panel["signal_date"].min(),
        "to",
        panel["signal_date"].max()
    )

    print("\nObservations by year:")
    print(
        panel.groupby(
            panel["signal_date"].dt.year
        ).size()
    )

    print("\nSample:")
    print(
        panel[
            [
                "permno",
                "ticker",
                "signal_date",
                "dlyprc",
                "dlycap",
                "prior_5d_return",
                "next_5d_return",
                "next_5d_market_return",
                "next_5d_excess_return"
            ]
        ].head(20)
    )


def main():

    print("Loading CRSP...")
    crsp = load_crsp(CRSP_FILE)

    print("Daily CRSP rows:")
    print(len(crsp))

    print("\nLoading S&P membership...")
    membership = load_sp500_membership(
        SP500_FILE
    )

    print("\nCalculating returns...")
    crsp = calculate_returns(crsp)

    print("\nCreating weekly observations...")
    weekly = create_weekly_signals(crsp)

    print("Weekly observations before membership filter:")
    print(len(weekly))

    print("\nApplying historical S&P membership...")
    weekly = filter_to_historical_sp500(
        weekly,
        membership
    )

    inspect_panel(weekly)

    columns_to_save = [
        "permno",
        "ticker",
        "issuernm",
        "signal_date",
        "week",
        "dlyprc",
        "dlycap",
        "prior_5d_return",
        "next_5d_return",
        "next_5d_market_return",
        "next_5d_excess_return"
    ]

    weekly[columns_to_save].to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"\nSaved to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()