import pandas as pd


IBES_FILE = "data/ibes_targets_linked_2005_2025.csv"
WEEKLY_CRSP_FILE = "data/weekly_crsp_panel.csv"

OUTPUT_FILE = "data/weekly_analyst_consensus.csv"

LOOKBACK_DAYS = 30


def load_ibes(file_path):
    """
    Load already-linked I/B/E/S targets.
    """

    df = pd.read_csv(file_path)

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )

    df["permno"] = pd.to_numeric(
        df["permno"],
        errors="coerce"
    )

    df["actdats"] = pd.to_datetime(
        df["actdats"],
        errors="coerce"
    )

    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce"
    )

    df["estimid"] = (
        df["estimid"]
        .astype(str)
        .str.strip()
    )

    df = df.dropna(
        subset=[
            "permno",
            "actdats",
            "estimid",
            "value"
        ]
    )

    return df


def load_weekly_crsp(file_path):
    """
    Load actual weekly signal dates.
    """

    df = pd.read_csv(file_path)

    df["signal_date"] = pd.to_datetime(
        df["signal_date"]
    )

    df["permno"] = pd.to_numeric(
        df["permno"],
        errors="coerce"
    )

    df["week"] = (
        df["signal_date"]
        .dt.to_period("W-FRI")
    )

    return df


def deduplicate_analyst_updates(ibes):
    """
    If the same analyst has multiple records on the
    same day for the same company, keep one final record.

    This prevents accidental double counting.
    """

    ibes = ibes.sort_values(
        [
            "permno",
            "estimid",
            "actdats"
        ]
    ).copy()

    ibes = ibes.drop_duplicates(
        subset=[
            "permno",
            "estimid",
            "actdats"
        ],
        keep="last"
    )

    return ibes


def create_active_intervals(
    ibes,
    lookback_days=30
):
    """
    Each target remains eligible until:

    1. the analyst publishes another target, OR
    2. the target becomes older than 30 days

    whichever happens first.
    """

    ibes = ibes.sort_values(
        [
            "permno",
            "estimid",
            "actdats"
        ]
    ).copy()

    # Next report from SAME analyst for SAME company
    ibes["next_report_date"] = (
        ibes
        .groupby(
            ["permno", "estimid"]
        )["actdats"]
        .shift(-1)
    )

    ibes["expiration_date"] = (
        ibes["actdats"]
        + pd.Timedelta(days=int(lookback_days))
    )

    return ibes


def expand_targets_to_candidate_weeks(ibes):
    """
    A 30-day target can affect at most roughly five
    weekly signal dates.

    Instead of generating:
        every week × every analyst

    we generate only a small number of possible weeks
    following each analyst report.
    """

    ibes = ibes.copy()

    ibes["start_week"] = (
        ibes["actdats"]
        .dt.to_period("W-FRI")
    )

    # Six is deliberately slightly conservative.
    offsets = pd.DataFrame(
        {
            "week_offset": range(6)
        }
    )

    expanded = (
        ibes.assign(key=1)
        .merge(
            offsets.assign(key=1),
            on="key"
        )
        .drop(columns="key")
    )

    expanded["week"] = (
        expanded["start_week"]
        +
        expanded["week_offset"]
    )

    return expanded


def match_targets_to_signal_dates(
    expanded,
    weekly
):
    """
    Match candidate analyst targets to the ACTUAL
    weekly CRSP signal dates.
    """

    signal_dates = (
        weekly[
            [
                "permno",
                "week",
                "signal_date"
            ]
        ]
        .drop_duplicates()
    )

    matched = expanded.merge(
        signal_dates,
        on=["permno", "week"],
        how="inner"
    )

    # Target must already have been active
    matched = matched[
        matched["signal_date"]
        >=
        matched["actdats"]
    ].copy()

    # Target can't be older than 30 days
    matched = matched[
        matched["signal_date"]
        <=
        matched["expiration_date"]
    ].copy()

    # If the analyst issued a newer target,
    # the old one stops being relevant.
    matched = matched[
        matched["next_report_date"].isna()
        |
        (
            matched["signal_date"]
            <
            matched["next_report_date"]
        )
    ].copy()

    return matched


def keep_latest_target_per_analyst(matched):
    """
    Extra safeguard:
    every analyst receives exactly one vote per
    company per signal date.
    """

    matched = matched.sort_values(
        [
            "permno",
            "signal_date",
            "estimid",
            "actdats"
        ]
    )

    matched = matched.drop_duplicates(
        subset=[
            "permno",
            "signal_date",
            "estimid"
        ],
        keep="last"
    )

    return matched


def calculate_consensus(matched):
    """
    Equal-weight all active analysts.
    """

    consensus = (
        matched
        .groupby(
            [
                "permno",
                "signal_date"
            ]
        )
        .agg(
            consensus_target=(
                "value",
                "mean"
            ),
            median_target=(
                "value",
                "median"
            ),
            analyst_count=(
                "value",
                "count"
            ),
            target_std=(
                "value",
                "std"
            ),
            min_target=(
                "value",
                "min"
            ),
            max_target=(
                "value",
                "max"
            ),
            newest_report_date=(
                "actdats",
                "max"
            ),
            oldest_report_date=(
                "actdats",
                "min"
            )
        )
        .reset_index()
    )

    return consensus


def add_target_revisions(
    consensus,
    weekly
):
    """
    Add previous-week consensus and calculate
    weekly target revision.

    Only count it as a one-week revision when
    the observations truly come from consecutive
    calendar weeks.
    """

    full = weekly[
        [
            "permno",
            "signal_date",
            "week"
        ]
    ].drop_duplicates()

    full = full.merge(
        consensus,
        on=[
            "permno",
            "signal_date"
        ],
        how="left"
    )

    full = full.sort_values(
        [
            "permno",
            "signal_date"
        ]
    )

    full["previous_consensus"] = (
        full
        .groupby("permno")
        ["consensus_target"]
        .shift(1)
    )

    full["previous_week"] = (
        full
        .groupby("permno")
        ["week"]
        .shift(1)
    )

    # Check that previous observation really was
    # the immediately preceding week.
    consecutive = (
        full["week"].astype("int64")
        -
        full["previous_week"].astype("int64")
    ) == 1

    full["target_revision_1w"] = pd.NA

    full.loc[
        consecutive,
        "target_revision_1w"
    ] = (
        full.loc[
            consecutive,
            "consensus_target"
        ]
        /
        full.loc[
            consecutive,
            "previous_consensus"
        ]
        - 1
    )

    return full


def inspect_consensus(df):
    """
    Print useful diagnostics.
    """

    available = df[
        df["consensus_target"].notna()
    ]

    print("\n================================")
    print("WEEKLY ANALYST CONSENSUS")
    print("================================")

    print("\nWeekly stock observations:")
    print(len(df))

    print("\nObservations with consensus:")
    print(len(available))

    print("\nCoverage:")
    print(
        f"{len(available) / len(df):.2%}"
    )

    print("\nUnique PERMNOs with consensus:")
    print(
        available["permno"].nunique()
    )

    print("\nAnalyst count distribution:")
    print(
        available["analyst_count"].describe()
    )

    print("\nSample:")
    print(
        available[
            [
                "permno",
                "signal_date",
                "consensus_target",
                "analyst_count",
                "target_std",
                "previous_consensus",
                "target_revision_1w"
            ]
        ].head(20)
    )

    print("\nConsensus coverage by year:")

    coverage = (
        df.assign(
            year=df["signal_date"].dt.year,
            has_consensus=df["consensus_target"].notna()
        )
        .groupby("year")
        .agg(
            total_observations=("has_consensus", "size"),
            observations_with_consensus=("has_consensus", "sum")
        )
    )

    coverage["coverage_rate"] = (
        coverage["observations_with_consensus"]
        /
        coverage["total_observations"]
    )

    print(coverage)

    print("\nConsensus observations with at least 3 analysts by year:")

    minimum_three = (
        df[
            df["analyst_count"] >= 3
        ]
        .assign(
            year=lambda x: x["signal_date"].dt.year
        )
        .groupby("year")
        .size()
    )

    print(minimum_three)


def main():

    print("Loading linked I/B/E/S data...")
    ibes = load_ibes(
        IBES_FILE
    )


    print("\nI/B/E/S date range:")
    print("Earliest:", ibes["actdats"].min())
    print("Latest:", ibes["actdats"].max())

    print("\nI/B/E/S observations by year:")
    print(
        ibes.groupby(
            ibes["actdats"].dt.year
        ).size()
    )

    print("Linked analyst observations:")
    print(len(ibes))

    print("\nLoading weekly CRSP panel...")
    weekly = load_weekly_crsp(
        WEEKLY_CRSP_FILE
    )

    print("Weekly CRSP observations:")
    print(len(weekly))

    print("\nDeduplicating analyst updates...")
    ibes = deduplicate_analyst_updates(
        ibes
    )

    print("After deduplication:")
    print(len(ibes))

    print("\nCreating analyst active intervals...")
    ibes = create_active_intervals(
        ibes,
        lookback_days=LOOKBACK_DAYS
    )

    print("\nExpanding reports into candidate weeks...")
    expanded = expand_targets_to_candidate_weeks(
        ibes
    )

    print("Candidate rows:")
    print(len(expanded))

    print("\nMatching reports to weekly signal dates...")
    matched = match_targets_to_signal_dates(
        expanded,
        weekly
    )

    print("Valid analyst-week matches:")
    print(len(matched))

    print("\nKeeping one target per analyst...")
    matched = keep_latest_target_per_analyst(
        matched
    )

    print(
        "Unique analyst votes:",
        len(matched)
    )

    print("\nCalculating equal-weight consensus...")
    consensus = calculate_consensus(
        matched
    )

    print("\nAdding analyst target revisions...")
    consensus = add_target_revisions(
        consensus,
        weekly
    )

    inspect_consensus(
        consensus
    )

    # Convert Period column to text before CSV
    consensus["week"] = consensus[
        "week"
    ].astype(str)

    consensus.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"\nSaved to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()