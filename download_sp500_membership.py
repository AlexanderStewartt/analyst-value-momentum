import pandas as pd


SP500_FILE = "data/sp500_ticker_start_end.csv"


def load_sp500_membership(file_path):
    """
    Load historical S&P 500 membership data.
    """

    df = pd.read_csv(file_path)

    df.columns = df.columns.str.strip().str.lower()

    df["start_date"] = pd.to_datetime(
        df["start_date"],
        errors="coerce"
    )

    df["end_date"] = pd.to_datetime(
        df["end_date"],
        errors="coerce"
    )

    df["ticker"] = (
        df["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # Blank end_date means the company was still a member
    # at the end of the dataset.
    df["end_date"] = df["end_date"].fillna(
        pd.Timestamp("2099-12-31")
    )

    return df


def filter_testing_period(
    membership,
    start_date="2005-01-01",
    end_date="2025-12-31"
):
    """
    Keep companies whose S&P 500 membership overlaps
    our desired research period.
    """

    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)

    filtered = membership[
        (membership["end_date"] >= start_date)
        &
        (membership["start_date"] <= end_date)
    ].copy()

    return filtered


def get_members_on_date(membership, date):
    """
    Return all companies that were S&P 500 members
    on a specific historical date.
    """

    date = pd.Timestamp(date)

    members = membership[
        (membership["start_date"] <= date)
        &
        (membership["end_date"] >= date)
    ].copy()

    return members


def inspect_membership(membership):
    """
    Print basic diagnostics.
    """

    print("\n========== S&P 500 MEMBERSHIP ==========")

    print("Rows:")
    print(len(membership))

    print("\nUnique tickers:")
    print(membership["ticker"].nunique())

    print("\nEarliest membership start:")
    print(membership["start_date"].min())

    print("\nLatest membership end:")
    print(membership["end_date"].max())

    print("\nFirst 10 rows:")
    print(membership.head(10))


def test_historical_dates(membership):
    """
    Check membership counts on several dates.
    """

    test_dates = [
        "2005-01-03",
        "2008-09-15",
        "2010-01-04",
        "2015-01-02",
        "2020-01-02",
        "2025-01-02"
    ]

    print("\n========== HISTORICAL MEMBERSHIP TEST ==========")

    for date in test_dates:

        members = get_members_on_date(
            membership,
            date
        )

        print(
            f"{date}: "
            f"{len(members)} members"
        )

        print(
            "Sample:",
            members["ticker"].head(10).tolist()
        )

        print()


def main():

    membership = load_sp500_membership(
        SP500_FILE
    )

    inspect_membership(membership)

    membership = filter_testing_period(
        membership,
        start_date="2005-01-01",
        end_date="2025-12-31"
    )

    print("\n========== 2005-2025 SAMPLE ==========")

    print(
        "Rows overlapping research period:",
        len(membership)
    )

    print(
        "Unique historical tickers:",
        membership["ticker"].nunique()
    )

    test_historical_dates(membership)


if __name__ == "__main__":
    main()
