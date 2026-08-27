import pandas as pd


IBES_FILE = "data/ibes_price_targets_2005_2025.csv"
LINK_FILE = "data/ibes_crsp_link_2005_2025.csv"

OUTPUT_FILE = "data/ibes_targets_linked_2005_2025.csv"


def load_ibes(file_path):
    """
    Load and clean raw I/B/E/S price-target observations.
    """

    ibes = pd.read_csv(file_path)

    # Make column names easier to use
    ibes.columns = (
        ibes.columns
        .str.strip()
        .str.lower()
    )

    # Clean ticker
    ibes["ticker"] = (
        ibes["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # Clean analyst/source identifier
    ibes["estimid"] = (
        ibes["estimid"]
        .astype(str)
        .str.strip()
    )

    # Clean analyst name
    ibes["alysnam"] = (
        ibes["alysnam"]
        .astype(str)
        .str.strip()
    )

    # Dates
    ibes["actdats"] = pd.to_datetime(
        ibes["actdats"],
        errors="coerce"
    )

    ibes["anndats"] = pd.to_datetime(
        ibes["anndats"],
        errors="coerce"
    )

    # Numeric fields
    ibes["horizon"] = pd.to_numeric(
        ibes["horizon"],
        errors="coerce"
    )

    ibes["value"] = pd.to_numeric(
        ibes["value"],
        errors="coerce"
    )

    return ibes


def load_link_table(file_path):
    """
    Load the historical I/B/E/S -> CRSP PERMNO mapping.
    """

    links = pd.read_csv(file_path)

    links.columns = (
        links.columns
        .str.strip()
        .str.lower()
    )

    links["ticker"] = (
        links["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    links["sdate"] = pd.to_datetime(
        links["sdate"],
        errors="coerce"
    )

    links["edate"] = pd.to_datetime(
        links["edate"],
        errors="coerce"
    )

    links["score"] = pd.to_numeric(
        links["score"],
        errors="coerce"
    )

    links["permno"] = pd.to_numeric(
        links["permno"],
        errors="coerce"
    )

    return links


def prepare_ibes(ibes):
    """
    Keep only observations relevant to our research.
    """

    # Price targets should be 12-month targets
    ibes = ibes[
        ibes["horizon"] == 12
    ].copy()

    # Need these fields to use an observation
    ibes = ibes.dropna(
        subset=[
            "ticker",
            "actdats",
            "estimid",
            "value"
        ]
    )

    # Remove obviously unusable target prices
    ibes = ibes[
        ibes["value"] > 0
    ].copy()

    return ibes


def prepare_links(links, max_score=2):
    """
    Keep only reasonably strong CRSP/I/B/E/S links.

    Lower WRDS scores represent better links.
    We start conservatively with scores 1 and 2.
    """

    links = links[
        links["score"] <= max_score
    ].copy()

    links = links.dropna(
        subset=[
            "ticker",
            "permno",
            "sdate",
            "edate"
        ]
    )

    return links


def attach_permno(ibes, links):
    """
    Attach the historically correct CRSP PERMNO to each
    I/B/E/S target observation.

    For every analyst observation:

        I/B/E/S ticker
        + ACTDATS

    is matched to the most recent link whose start date
    occurred before or on ACTDATS.

    We then confirm ACTDATS is also before the link's end date.
    """

    # merge_asof is much faster than looping through
    # every analyst report individually.

    ibes = ibes.sort_values(
        ["actdats", "ticker"]
    ).copy()

    links = links.sort_values(
        ["sdate", "ticker"]
    ).copy()

    linked = pd.merge_asof(
        ibes,
        links[
            [
                "ticker",
                "permno",
                "ncusip",
                "sdate",
                "edate",
                "score"
            ]
        ],
        left_on="actdats",
        right_on="sdate",
        by="ticker",
        direction="backward",
        allow_exact_matches=True
    )

    # A backward match might find an old link that had
    # already expired. Remove those.
    valid_link = (
        linked["permno"].notna()
        &
        (linked["actdats"] <= linked["edate"])
    )

    linked["valid_crsp_link"] = valid_link

    return linked


def inspect_results(linked):
    """
    Print diagnostics before saving.
    """

    print("\n======================================")
    print("I/B/E/S -> CRSP LINKING RESULTS")
    print("======================================")

    print("\nTotal target observations:")
    print(len(linked))

    valid = linked[
        linked["valid_crsp_link"]
    ]

    invalid = linked[
        ~linked["valid_crsp_link"]
    ]

    print("\nSuccessfully linked observations:")
    print(len(valid))

    print("\nUnlinked observations:")
    print(len(invalid))

    if len(linked) > 0:
        print(
            "\nPercent successfully linked:",
            f"{len(valid) / len(linked):.2%}"
        )

    print("\nUnique linked PERMNOs:")
    print(valid["permno"].nunique())

    print("\nLink score distribution:")
    print(
        valid["score"]
        .value_counts()
        .sort_index()
    )

    print("\nMost common unmatched I/B/E/S tickers:")
    print(
        invalid["ticker"]
        .value_counts()
        .head(20)
    )

    print("\nSample linked observations:")

    sample_columns = [
        "ticker",
        "oftic",
        "cname",
        "actdats",
        "estimid",
        "alysnam",
        "value",
        "permno",
        "score"
    ]

    print(
        valid[sample_columns]
        .head(20)
    )


def save_linked_data(linked, output_path):
    """
    Save only observations that received a valid CRSP link.
    """

    linked = linked[
        linked["valid_crsp_link"]
    ].copy()

    columns_to_keep = [
        "permno",
        "ticker",
        "oftic",
        "cname",
        "actdats",
        "anndats",
        "estimid",
        "alysnam",
        "horizon",
        "value",
        "ncusip",
        "score"
    ]

    linked = linked[
        columns_to_keep
    ]

    # PERMNO should behave like an integer identifier
    linked["permno"] = linked["permno"].astype("Int64")

    linked = linked.sort_values(
        [
            "permno",
            "actdats",
            "estimid"
        ]
    )

    linked.to_csv(
        output_path,
        index=False
    )

    print(
        f"\nSaved linked analyst data to:\n{output_path}"
    )

    print(
        "Rows saved:",
        len(linked)
    )


def main():

    print("Loading I/B/E/S data...")
    ibes = load_ibes(IBES_FILE)

    print("Loading historical CRSP link table...")
    links = load_link_table(LINK_FILE)

    print("\nRaw I/B/E/S rows:")
    print(len(ibes))

    print("Raw link rows:")
    print(len(links))

    # ---------------------------------
    # Clean/filter
    # ---------------------------------

    ibes = prepare_ibes(ibes)

    links = prepare_links(
        links,
        max_score=2
    )

    print("\n12-month valid target rows:")
    print(len(ibes))

    print("High-quality link rows:")
    print(len(links))

    # ---------------------------------
    # Historical identifier linking
    # ---------------------------------

    linked = attach_permno(
        ibes,
        links
    )

    # ---------------------------------
    # Diagnostics
    # ---------------------------------

    inspect_results(linked)

    # ---------------------------------
    # Save
    # ---------------------------------

    save_linked_data(
        linked,
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()