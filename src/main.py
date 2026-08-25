import pandas as pd


CRSP_FILE = "data/crsp_prices.csv"
IBES_FILE = "data/ibes_targets.csv"


def load_crsp_data(file_path):
    """
    Load CRSP daily stock data.
    """
    df = pd.read_csv(file_path)

    # Make column names easier to work with
    df.columns = df.columns.str.strip().str.lower()

    return df


def load_ibes_data(file_path):
    """
    Load I/B/E/S analyst price target data.
    """
    df = pd.read_csv(file_path)

    # Make column names easier to work with
    df.columns = df.columns.str.strip().str.lower()

    return df


def clean_crsp_data(df):
    """
    Basic cleaning for CRSP data.
    """

    # Convert date column into actual datetime objects
    if "dlycaldt" in df.columns:
        df["dlycaldt"] = pd.to_datetime(df["dlycaldt"])

    # Make ticker consistently uppercase
    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()

    return df


def clean_ibes_data(df):
    """
    Clean I/B/E/S analyst target data.
    """

    df = df.copy()

    if "actdats" in df.columns:
        df["actdats"] = pd.to_datetime(
            df["actdats"],
            errors="coerce"
        )

    if "anndats" in df.columns:
        df["anndats"] = pd.to_datetime(
            df["anndats"],
            errors="coerce"
        )

    if "ticker" in df.columns:
        df["ticker"] = (
            df["ticker"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    if "oftic" in df.columns:
        df["oftic"] = (
            df["oftic"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    if "alysnam" in df.columns:
        df["alysnam"] = (
            df["alysnam"]
            .astype(str)
            .str.strip()
        )

    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce"
    )

    return df

def calculate_returns(crsp):
    """
    Calculate previous 5-day return and
    subsequent 5-day return for each stock.
    """

    crsp = crsp.sort_values(["permno", "dlycaldt"]).copy()

    crsp["dlyret"] = pd.to_numeric(
        crsp["dlyret"],
        errors="coerce"
    )

    # Previous 5 trading days, including today
    crsp["prior_5d_return"] = (
        crsp.groupby("permno")["dlyret"]
        .transform(
            lambda returns:
                (1 + returns)
                .rolling(5)
                .apply(lambda x: x.prod() - 1, raw=True)
        )
    )

    # Next 5 trading days, starting tomorrow
    crsp["next_5d_return"] = (
        crsp.groupby("permno")["dlyret"]
        .transform(
            lambda returns:
                (1 + returns)
                .rolling(5)
                .apply(lambda x: x.prod() - 1, raw=True)
                .shift(-5)
        )
    )

    return crsp

def inspect_data(crsp, ibes):
    """
    Print basic information so we can confirm
    that the datasets loaded correctly.
    """

    print("\n========== CRSP DATA ==========")
    print("Shape:", crsp.shape)

    print("\nColumns:")
    print(crsp.columns.tolist())

    print("\nFirst 5 rows:")
    print(crsp.head())

    print("\nTickers:")
    if "ticker" in crsp.columns:
        print(crsp["ticker"].unique())

    print("\n========== IBES DATA ==========")
    print("Shape:", ibes.shape)

    print("\nColumns:")
    print(ibes.columns.tolist())

    print("\nFirst 5 rows:")
    print(ibes.head())

    print("\nTickers:")
    if "ticker" in ibes.columns:
        print(ibes["ticker"].unique())

def save_clean_crsp(crsp, output_path):
    """
    Save the cleaned CRSP dataset with the variables
    needed for the momentum study.
    """

    columns_to_keep = [
        "permno",
        "ticker",
        "securitynm",
        "dlycaldt",
        "dlyprc",
        "dlycap",
        "dlyret",
        "sprtrn",
        "prior_5d_return",
        "next_5d_return"
    ]

    clean = crsp[columns_to_keep].copy()

    clean.to_csv(output_path, index=False)

    print(f"\nSaved cleaned CRSP data to: {output_path}")
    print("Rows saved:", len(clean))

def create_weekly_signals(crsp):
    """
    Keep only the final trading day of each week.

    prior_5d_return:
        return over the 5 trading days ending on signal_date

    next_5d_return:
        return over the next 5 trading days after signal_date
    """

    crsp = crsp.sort_values(["permno", "dlycaldt"]).copy()

    # Each period ends on Friday.
    # If Friday is a holiday, the final trading day might be Thursday.
    crsp["week"] = crsp["dlycaldt"].dt.to_period("W-FRI")

    weekly = (
        crsp.groupby(["permno", "week"], as_index=False)
        .tail(1)
        .copy()
    )

    weekly = weekly.rename(
        columns={"dlycaldt": "signal_date"}
    )

    weekly = weekly.drop(columns=["week"])

    return weekly

def build_analyst_consensus(
    weekly,
    ibes,
    lookback_days=30
):
    """
    Construct a point-in-time analyst consensus for every
    stock-week.

    For each signal date:
        1. Look backward lookback_days.
        2. For each analyst, use ONLY their most recent target.
        3. Give all analysts equal weight.
        4. Calculate consensus statistics.

    ACTDATS is treated as the date the estimate became
    available to us.
    """

    # For our initial prototype, use OFTIC because it tends to
    # correspond more closely with the CRSP trading ticker.
    analyst_data = ibes[
        [
            "oftic",
            "actdats",
            "alysnam",
            "value"
        ]
    ].copy()

    analyst_data = analyst_data.rename(
        columns={"oftic": "ticker"}
    )

    analyst_data = analyst_data.dropna(
        subset=[
            "ticker",
            "actdats",
            "alysnam",
            "value"
        ]
    )

    analyst_data = analyst_data[
        analyst_data["value"] > 0
    ]

    results = []

    # Processing one ticker at a time keeps memory usage reasonable
    # when we eventually scale to hundreds of companies.
    for ticker, stock_weeks in weekly.groupby("ticker"):

        stock_targets = analyst_data[
            analyst_data["ticker"] == ticker
        ].copy()

        if stock_targets.empty:
            continue

        stock_weeks = (
            stock_weeks[
                ["ticker", "signal_date"]
            ]
            .drop_duplicates()
            .sort_values("signal_date")
        )

        analysts = stock_targets[
            "alysnam"
        ].drop_duplicates()

        # Create:
        #
        # every signal date × every analyst covering the company
        #
        grid = (
            stock_weeks.assign(key=1)
            .merge(
                pd.DataFrame(
                    {
                        "alysnam": analysts,
                        "key": 1
                    }
                ),
                on="key"
            )
            .drop(columns="key")
        )

        grid = grid.sort_values(
            ["signal_date", "alysnam"]
        )

        stock_targets = stock_targets.sort_values(
            ["actdats", "alysnam"]
        )

        # For every analyst/date pair, find that analyst's
        # most recent target BEFORE OR ON the signal date.
        matched = pd.merge_asof(
            grid.sort_values("signal_date"),
            stock_targets[
                [
                    "actdats",
                    "alysnam",
                    "value"
                ]
            ].sort_values("actdats"),
            left_on="signal_date",
            right_on="actdats",
            by="alysnam",
            direction="backward",
            allow_exact_matches=True
        )

        # How old was that analyst target?
        matched["target_age_days"] = (
            matched["signal_date"]
            -
            matched["actdats"]
        ).dt.days

        # Only keep estimates published within our lookback window.
        matched = matched[
            (matched["target_age_days"] >= 0)
            &
            (
                matched["target_age_days"]
                <= lookback_days
            )
        ]

        if matched.empty:
            continue

        consensus = (
            matched.groupby(
                ["ticker", "signal_date"]
            )
            .agg(
                consensus_target=("value", "mean"),
                median_target=("value", "median"),
                analyst_count=("value", "count"),
                target_std=("value", "std"),
                min_target=("value", "min"),
                max_target=("value", "max"),
                newest_target_date=("actdats", "max"),
                oldest_target_date=("actdats", "min")
            )
            .reset_index()
        )

        results.append(consensus)

    if not results:
        return pd.DataFrame()

    return pd.concat(
        results,
        ignore_index=True
    )

def create_research_panel(
    weekly,
    consensus
):
    """
    Merge stock momentum/return information with
    analyst consensus values.
    """

    panel = weekly.merge(
        consensus,
        on=["ticker", "signal_date"],
        how="left"
    )

    # Analysts' expected upside relative to current PRICE
    panel["target_upside"] = (
        panel["consensus_target"]
        /
        panel["dlyprc"]
    ) - 1

    # Actual discount of market price relative to estimated VALUE
    #
    # Example:
    #
    # Fair value = $100
    # Price      = $80
    #
    # Discount = 20%
    #
    panel["discount_to_consensus"] = (
        panel["consensus_target"]
        -
        panel["dlyprc"]
    ) / panel["consensus_target"]

    return panel

def analyze_value_momentum(
    panel,
    discount_threshold=0.20,
    momentum_threshold=0.03,
    minimum_analysts=3
):
    """
    Test whether stocks with strong positive momentum AND
    substantial analyst-implied undervaluation are more
    likely to have positive returns during the following week.

    Parameters
    ----------
    discount_threshold:
        Minimum discount to analyst consensus value.
        0.20 = stock is at least 20% below estimated value.

    momentum_threshold:
        Minimum previous 5-day return.
        0.03 = previous week gained at least 3%.

    minimum_analysts:
        Minimum analyst count required for consensus.
    """

    data = panel.dropna(
        subset=[
            "prior_5d_return",
            "next_5d_return",
            "discount_to_consensus",
            "analyst_count"
        ]
    ).copy()

    # Avoid calling one analyst's opinion "consensus"
    data = data[
        data["analyst_count"]
        >= minimum_analysts
    ]

    # First-week positive momentum
    momentum = data[
        data["prior_5d_return"]
        >= momentum_threshold
    ].copy()

    # Momentum AND materially undervalued
    value_momentum = momentum[
        momentum["discount_to_consensus"]
        >= discount_threshold
    ].copy()

    # Momentum but NOT sufficiently undervalued
    momentum_only = momentum[
        momentum["discount_to_consensus"]
        < discount_threshold
    ].copy()

    def calculate_stats(group):

        if len(group) == 0:
            return {
                "observations": 0,
                "positive_next_week_rate": float("nan"),
                "average_next_week_return": float("nan"),
                "median_next_week_return": float("nan")
            }

        return {
            "observations": len(group),

            "positive_next_week_rate":
                (group["next_5d_return"] > 0).mean(),

            "average_next_week_return":
                group["next_5d_return"].mean(),

            "median_next_week_return":
                group["next_5d_return"].median()
        }

    value_stats = calculate_stats(
        value_momentum
    )

    momentum_stats = calculate_stats(
        momentum_only
    )

    all_momentum_stats = calculate_stats(
        momentum
    )

    print("\n========================================")
    print("VALUE + MOMENTUM ANALYSIS")
    print("========================================")

    print(
        f"\nMomentum threshold: "
        f"{momentum_threshold:.1%}"
    )

    print(
        f"Discount threshold: "
        f"{discount_threshold:.1%}"
    )

    print(
        f"Minimum analysts: "
        f"{minimum_analysts}"
    )

    print(
        "\n--- MOMENTUM + UNDERVALUED ---"
    )

    print(
        f"Observations: "
        f"{value_stats['observations']}"
    )

    print(
        "Positive next week: "
        f"{value_stats['positive_next_week_rate']:.2%}"
    )

    print(
        "Average next-week return: "
        f"{value_stats['average_next_week_return']:.2%}"
    )

    print(
        "Median next-week return: "
        f"{value_stats['median_next_week_return']:.2%}"
    )

    print(
        "\n--- MOMENTUM BUT NOT UNDERVALUED ---"
    )

    print(
        f"Observations: "
        f"{momentum_stats['observations']}"
    )

    print(
        "Positive next week: "
        f"{momentum_stats['positive_next_week_rate']:.2%}"
    )

    print(
        "Average next-week return: "
        f"{momentum_stats['average_next_week_return']:.2%}"
    )

    print(
        "Median next-week return: "
        f"{momentum_stats['median_next_week_return']:.2%}"
    )

    if (
        value_stats["observations"] > 0
        and
        momentum_stats["observations"] > 0
    ):

        probability_difference = (
            value_stats[
                "positive_next_week_rate"
            ]
            -
            momentum_stats[
                "positive_next_week_rate"
            ]
        )

        return_difference = (
            value_stats[
                "average_next_week_return"
            ]
            -
            momentum_stats[
                "average_next_week_return"
            ]
        )

        print("\n--- DIFFERENCE ---")

        print(
            "Increase in probability of "
            "positive next week: "
            f"{probability_difference:.2%}"
        )

        print(
            "Difference in average "
            "next-week return: "
            f"{return_difference:.2%}"
        )

    return {
        "value_momentum": value_stats,
        "momentum_only": momentum_stats,
        "all_momentum": all_momentum_stats
    }
def inspect_qualifying_observations(
    panel,
    discount_threshold=0.20,
    momentum_threshold=0.03,
    minimum_analysts=3
):

    qualifying = panel[
        (panel["prior_5d_return"] >= momentum_threshold)
        &
        (panel["discount_to_consensus"] >= discount_threshold)
        &
        (panel["analyst_count"] >= minimum_analysts)
    ].copy()

    qualifying["year"] = qualifying["signal_date"].dt.year

    print("\n===== QUALIFYING OBSERVATIONS BY TICKER =====")
    print(
        qualifying.groupby("ticker")
        .size()
        .sort_values(ascending=False)
    )

    print("\n===== QUALIFYING OBSERVATIONS BY YEAR =====")
    print(
        qualifying.groupby("year")
        .size()
        .sort_index()
    )

    print("\n===== ACTUAL OBSERVATIONS =====")

    print(
        qualifying[
            [
                "ticker",
                "signal_date",
                "dlyprc",
                "prior_5d_return",
                "consensus_target",
                "discount_to_consensus",
                "analyst_count",
                "next_5d_return"
            ]
        ].sort_values("signal_date")
    )

    return qualifying

def main():

    # =========================
    # LOAD DATA
    # =========================

    crsp = load_crsp_data(CRSP_FILE)
    ibes = load_ibes_data(IBES_FILE)

    # =========================
    # CLEAN DATA
    # =========================

    crsp = clean_crsp_data(crsp)
    ibes = clean_ibes_data(ibes)

    # =========================
    # CALCULATE RETURNS
    # =========================

    crsp = calculate_returns(crsp)

    # =========================
    # CREATE WEEKLY SIGNAL DATES
    # =========================

    weekly = create_weekly_signals(crsp)

    print(
        "\nWeekly observations:",
        len(weekly)
    )

    # =========================
    # ANALYST CONSENSUS
    # =========================

    consensus = build_analyst_consensus(
        weekly,
        ibes,
        lookback_days=30
    )

    print(
        "Weekly observations with analyst consensus:",
        len(consensus)
    )

    # =========================
    # MERGE EVERYTHING
    # =========================

    panel = create_research_panel(
        weekly,
        consensus
    )

    # Save our main research dataset
    panel.to_csv(
        "data/weekly_research_panel.csv",
        index=False
    )

    print(
        "\nSaved research panel to:"
        " data/weekly_research_panel.csv"
    )

    # =========================
    # RUN FIRST HYPOTHESIS TEST
    # =========================

    analyze_value_momentum(
        panel,
        discount_threshold=0.20,
        momentum_threshold=0.03,
        minimum_analysts=3
    )

    inspect_qualifying_observations(panel)


if __name__ == "__main__":
    main()