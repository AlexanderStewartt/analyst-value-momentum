import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import numpy as np


CRSP_FILE = "data/weekly_crsp_panel.csv"
ANALYST_FILE = "data/weekly_analyst_consensus.csv"


def load_crsp(file_path):
    """
    Load the processed weekly CRSP panel.
    """

    df = pd.read_csv(file_path)

    df.columns = df.columns.str.strip().str.lower()

    df["signal_date"] = pd.to_datetime(
        df["signal_date"],
        errors="coerce"
    )

    df["permno"] = pd.to_numeric(
        df["permno"],
        errors="coerce"
    )

    numeric_columns = [
        "dlyprc",
        "dlycap",
        "prior_5d_return",
        "next_5d_return",
        "next_5d_market_return",
        "next_5d_excess_return"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    return df


def load_analyst_consensus(file_path):
    """
    Load the processed weekly analyst consensus.
    """

    df = pd.read_csv(file_path)

    df.columns = df.columns.str.strip().str.lower()

    df["signal_date"] = pd.to_datetime(
        df["signal_date"],
        errors="coerce"
    )

    df["permno"] = pd.to_numeric(
        df["permno"],
        errors="coerce"
    )

    numeric_columns = [
        "consensus_target",
        "analyst_count",
        "target_std",
        "previous_consensus",
        "target_revision_1w"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    return df


def create_research_panel(crsp, analysts):
    """
    Merge CRSP stock-week observations with the analyst
    consensus available on the same signal date.
    """

    analyst_columns = [
        "permno",
        "signal_date",
        "consensus_target",
        "analyst_count",
        "target_std",
        "previous_consensus",
        "target_revision_1w"
    ]

    panel = crsp.merge(
        analysts[analyst_columns],
        on=["permno", "signal_date"],
        how="left"
    )

    # ------------------------------------------
    # Analyst-implied valuation measures
    # ------------------------------------------

    # Example:
    #
    # price = 80
    # consensus value = 100
    #
    # discount = 20%
    #
    panel["discount_to_consensus"] = (
        panel["consensus_target"] - panel["dlyprc"]
    ) / panel["consensus_target"]

    # This is a related but different measure:
    #
    # price = 80
    # target = 100
    #
    # upside = 25%
    #
    panel["target_upside"] = (
        panel["consensus_target"]
        / panel["dlyprc"]
    ) - 1

    return panel


def calculate_group_statistics(group):
    """
    Calculate statistics for one group of stock-week observations.
    """

    if len(group) == 0:
        return {
            "observations": 0,
            "positive_next_week_rate": float("nan"),
            "average_next_week_return": float("nan"),
            "median_next_week_return": float("nan"),
            "average_excess_return": float("nan")
        }

    return {
        "observations": len(group),

        "positive_next_week_rate":
            (group["next_5d_return"] > 0).mean(),

        "average_next_week_return":
            group["next_5d_return"].mean(),

        "median_next_week_return":
            group["next_5d_return"].median(),

        "average_excess_return":
            group["next_5d_excess_return"].mean()
    }


def test_positive_momentum_and_undervaluation(
    panel,
    discount_threshold=0.20,
    momentum_threshold=0.00,
    minimum_analysts=3
):
    """
    Main hypothesis test.

    Question:

    Given that a stock had a positive previous week,
    is it more likely to have another positive week
    when it trades at least 20% below analyst consensus value?

    Parameters
    ----------
    discount_threshold:
        0.20 means market price is at least 20%
        below analyst consensus value.

    momentum_threshold:
        0.00 means ANY positive prior five-day return qualifies.

        Later this can easily be changed to:
            0.01
            0.03
            0.05
            etc.

    minimum_analysts:
        Minimum number of analysts required for the
        consensus estimate.
    """

    # ------------------------------------------
    # Keep observations with everything required
    # ------------------------------------------

    data = panel.dropna(
        subset=[
            "prior_5d_return",
            "next_5d_return",
            "consensus_target",
            "discount_to_consensus",
            "analyst_count"
        ]
    ).copy()

    # Require a reasonably meaningful consensus
    data = data[
        data["analyst_count"] >= minimum_analysts
    ].copy()

    # ------------------------------------------
    # Positive prior-week momentum
    # ------------------------------------------

    positive_momentum = data[
        data["prior_5d_return"] > momentum_threshold
    ].copy()

    # ------------------------------------------
    # Divide those stocks by valuation
    # ------------------------------------------

    undervalued = positive_momentum[
        positive_momentum["discount_to_consensus"]
        >= discount_threshold
    ].copy()

    not_undervalued = positive_momentum[
        positive_momentum["discount_to_consensus"]
        < discount_threshold
    ].copy()

    # ------------------------------------------
    # Statistics
    # ------------------------------------------

    undervalued_stats = calculate_group_statistics(
        undervalued
    )

    comparison_stats = calculate_group_statistics(
        not_undervalued
    )

    all_positive_stats = calculate_group_statistics(
        positive_momentum
    )

    # ------------------------------------------
    # Print result
    # ------------------------------------------

    print("\n================================================")
    print("POSITIVE MOMENTUM + ANALYST UNDERVALUATION TEST")
    print("================================================")

    print(
        f"\nPrior-week momentum requirement: "
        f"> {momentum_threshold:.1%}"
    )

    print(
        f"Undervaluation requirement: "
        f">= {discount_threshold:.1%}"
    )

    print(
        f"Minimum analysts: "
        f"{minimum_analysts}"
    )

    print("\n----------------------------------------")
    print("POSITIVE MOMENTUM + >=20% UNDERVALUED")
    print("----------------------------------------")

    print(
        f"Observations: "
        f"{undervalued_stats['observations']:,}"
    )

    print(
        "Probability next week is positive: "
        f"{undervalued_stats['positive_next_week_rate']:.2%}"
    )

    print(
        "Average next-week return: "
        f"{undervalued_stats['average_next_week_return']:.3%}"
    )

    print(
        "Median next-week return: "
        f"{undervalued_stats['median_next_week_return']:.3%}"
    )

    print(
        "Average S&P-adjusted return: "
        f"{undervalued_stats['average_excess_return']:.3%}"
    )

    print("\n----------------------------------------")
    print("POSITIVE MOMENTUM + <20% UNDERVALUED")
    print("----------------------------------------")

    print(
        f"Observations: "
        f"{comparison_stats['observations']:,}"
    )

    print(
        "Probability next week is positive: "
        f"{comparison_stats['positive_next_week_rate']:.2%}"
    )

    print(
        "Average next-week return: "
        f"{comparison_stats['average_next_week_return']:.3%}"
    )

    print(
        "Median next-week return: "
        f"{comparison_stats['median_next_week_return']:.3%}"
    )

    print(
        "Average S&P-adjusted return: "
        f"{comparison_stats['average_excess_return']:.3%}"
    )

    # ------------------------------------------
    # Difference between groups
    # ------------------------------------------

    probability_difference = (
        undervalued_stats["positive_next_week_rate"]
        -
        comparison_stats["positive_next_week_rate"]
    )

    return_difference = (
        undervalued_stats["average_next_week_return"]
        -
        comparison_stats["average_next_week_return"]
    )

    excess_return_difference = (
        undervalued_stats["average_excess_return"]
        -
        comparison_stats["average_excess_return"]
    )

    print("\n========================================")
    print("DIFFERENCE")
    print("========================================")

    print(
        "Difference in probability of positive next week: "
        f"{probability_difference:+.2%}"
    )

    print(
        "Difference in average next-week return: "
        f"{return_difference:+.3%}"
    )

    print(
        "Difference in S&P-adjusted return: "
        f"{excess_return_difference:+.3%}"
    )

    print("\n----------------------------------------")
    print("ALL POSITIVE-MOMENTUM OBSERVATIONS")
    print("----------------------------------------")

    print(
        f"Observations: "
        f"{all_positive_stats['observations']:,}"
    )

    print(
        "Probability next week is positive: "
        f"{all_positive_stats['positive_next_week_rate']:.2%}"
    )

    return {
        "undervalued": undervalued_stats,
        "not_undervalued": comparison_stats,
        "all_positive_momentum": all_positive_stats
    }
def add_analysis_buckets(panel):
    """
    Create momentum and analyst-discount buckets.

    Momentum is based on prior 5-day return.
    Discount is based on:
        (consensus_target - price) / consensus_target
    """

    df = panel.copy()

    # Only keep rows with the data required for this analysis
    df = df.dropna(
        subset=[
            "prior_5d_return",
            "next_5d_return",
            "next_5d_excess_return",
            "discount_to_consensus",
            "analyst_count"
        ]
    )

    # Require a meaningful analyst consensus
    df = df[
        df["analyst_count"] >= 3
    ].copy()

    # -----------------------------
    # Momentum buckets
    # -----------------------------
    momentum_bins = [
        float("-inf"),
        0.00,
        0.01,
        0.03,
        0.05,
        0.10,
        float("inf")
    ]

    momentum_labels = [
        "< 0%",
        "0% to 1%",
        "1% to 3%",
        "3% to 5%",
        "5% to 10%",
        ">= 10%"
    ]

    df["momentum_bucket"] = pd.cut(
        df["prior_5d_return"],
        bins=momentum_bins,
        labels=momentum_labels,
        right=False
    )

    # -----------------------------
    # Analyst discount buckets
    # -----------------------------
    discount_bins = [
        float("-inf"),
        0.00,
        0.10,
        0.20,
        0.30,
        0.40,
        float("inf")
    ]

    discount_labels = [
        "< 0%",
        "0% to 10%",
        "10% to 20%",
        "20% to 30%",
        "30% to 40%",
        ">= 40%"
    ]

    df["discount_bucket"] = pd.cut(
        df["discount_to_consensus"],
        bins=discount_bins,
        labels=discount_labels,
        right=False
    )

    return df


def build_momentum_discount_matrix(df):
    """
    Summarize outcomes for every momentum x discount bucket.
    """

    grouped = (
        df.groupby(
            [
                "momentum_bucket",
                "discount_bucket"
            ],
            observed=True
        )
        .agg(
            observations=(
                "next_5d_return",
                "size"
            ),

            positive_next_week_rate=(
                "next_5d_return",
                lambda x: (x > 0).mean()
            ),

            average_next_week_return=(
                "next_5d_return",
                "mean"
            ),

            average_excess_return=(
                "next_5d_excess_return",
                "mean"
            ),

            median_next_week_return=(
                "next_5d_return",
                "median"
            )
        )
        .reset_index()
    )

    return grouped

def print_matrices(results):
    """
    Print pivot tables for the major outcomes.
    """

    probability_matrix = results.pivot(
        index="momentum_bucket",
        columns="discount_bucket",
        values="positive_next_week_rate"
    )

    return_matrix = results.pivot(
        index="momentum_bucket",
        columns="discount_bucket",
        values="average_next_week_return"
    )

    excess_matrix = results.pivot(
        index="momentum_bucket",
        columns="discount_bucket",
        values="average_excess_return"
    )

    count_matrix = results.pivot(
        index="momentum_bucket",
        columns="discount_bucket",
        values="observations"
    )

    print("\n========================================")
    print("PROBABILITY NEXT WEEK IS POSITIVE")
    print("========================================")
    print(
        probability_matrix
        .map(lambda x: f"{x:.2%}" if pd.notna(x) else "")
    )

    print("\n========================================")
    print("AVERAGE NEXT-WEEK RETURN")
    print("========================================")
    print(
        return_matrix
        .map(lambda x: f"{x:.3%}" if pd.notna(x) else "")
    )

    print("\n========================================")
    print("AVERAGE S&P-ADJUSTED RETURN")
    print("========================================")
    print(
        excess_matrix
        .map(lambda x: f"{x:.3%}" if pd.notna(x) else "")
    )

    print("\n========================================")
    print("OBSERVATION COUNTS")
    print("========================================")
    print(
        count_matrix.fillna(0).astype(int)
    )

    return (
        probability_matrix,
        return_matrix,
        excess_matrix,
        count_matrix
    )
def create_probability_heatmap(probability_matrix):
    """
    Create a heatmap showing the probability that the next
    5-day return is positive for each momentum/discount combination.
    """

    # Convert probabilities from decimals to percentages
    values = probability_matrix.to_numpy() * 100

    fig, ax = plt.subplots(figsize=(10, 7))

    heatmap = ax.imshow(
        values,
        aspect="auto"
    )

    # Axis labels
    ax.set_xticks(range(len(probability_matrix.columns)))
    ax.set_xticklabels(
        probability_matrix.columns,
        rotation=45,
        ha="right"
    )

    ax.set_yticks(range(len(probability_matrix.index)))
    ax.set_yticklabels(probability_matrix.index)

    ax.set_xlabel("Discount to Analyst Consensus")
    ax.set_ylabel("Prior 5-Day Return")

    ax.set_title(
        "Probability of Positive Next-Week Return\n"
        "by Prior-Week Momentum and Analyst-Implied Discount"
    )

    # Put the actual percentage inside every cell
    for row in range(values.shape[0]):
        for col in range(values.shape[1]):

            value = values[row, col]

            if pd.notna(value):
                ax.text(
                    col,
                    row,
                    f"{value:.1f}%",
                    ha="center",
                    va="center"
                )

    # Color scale
    colorbar = fig.colorbar(
        heatmap,
        ax=ax
    )

    colorbar.set_label(
        "Probability Next Week Is Positive (%)"
    )

    plt.tight_layout()

    # Save it for GitHub / README later
    plt.savefig(
        "data/momentum_discount_probability_heatmap.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()
def add_same_week_baseline(panel, min_analysts=3):
    """
    Calculate the contemporaneous cross-sectional baseline.

    For every signal_date:
        baseline = fraction of eligible stocks whose
        next 5-day return is positive.

    Each stock-week then receives the baseline probability
    corresponding to its own signal week.
    """

    df = panel.copy()

    # Same eligible universe used in our analysis
    df = df.dropna(
        subset=[
            "prior_5d_return",
            "next_5d_return",
            "discount_to_consensus",
            "analyst_count"
        ]
    )

    df = df[
        df["analyst_count"] >= min_analysts
    ].copy()

    # 1 if stock is positive next week, otherwise 0
    df["next_week_positive"] = (
        df["next_5d_return"] > 0
    ).astype(int)

    # For each week, calculate percentage of eligible stocks
    # that are positive the following week
    df["same_week_positive_baseline"] = (
        df.groupby("signal_date")["next_week_positive"]
        .transform("mean")
    )

    return df
def build_same_week_comparison(df):
    """
    Compare each momentum/discount bucket against the
    contemporaneous cross-sectional baseline.
    """

    df = add_analysis_buckets(df)

    results = (
        df.groupby(
            [
                "momentum_bucket",
                "discount_bucket"
            ],
            observed=True
        )
        .agg(
            observations=(
                "next_week_positive",
                "size"
            ),

            signal_positive_rate=(
                "next_week_positive",
                "mean"
            ),

            average_same_week_baseline=(
                "same_week_positive_baseline",
                "mean"
            ),

            average_next_week_return=(
                "next_5d_return",
                "mean"
            )
        )
        .reset_index()
    )

    # Percentage-point difference
    results["probability_advantage_pp"] = (
        results["signal_positive_rate"]
        -
        results["average_same_week_baseline"]
    ) * 100

    return results
def print_same_week_comparison(results):

    advantage_matrix = results.pivot(
        index="momentum_bucket",
        columns="discount_bucket",
        values="probability_advantage_pp"
    )

    baseline_matrix = results.pivot(
        index="momentum_bucket",
        columns="discount_bucket",
        values="average_same_week_baseline"
    )

    signal_matrix = results.pivot(
        index="momentum_bucket",
        columns="discount_bucket",
        values="signal_positive_rate"
    )

    print("\n========================================")
    print("SAME-WEEK CROSS-SECTIONAL COMPARISON")
    print("========================================")

    print("\nSIGNAL POSITIVE RATE:")
    print(
        signal_matrix.map(
            lambda x: f"{x:.2%}" if pd.notna(x) else ""
        )
    )

    print("\nAVERAGE SAME-WEEK S&P STOCK BASELINE:")
    print(
        baseline_matrix.map(
            lambda x: f"{x:.2%}" if pd.notna(x) else ""
        )
    )

    print("\nADVANTAGE VS SAME-WEEK BASELINE:")
    print(
        advantage_matrix.map(
            lambda x: f"{x:+.2f} pp" if pd.notna(x) else ""
        )
    )

    return advantage_matrix
def create_same_week_advantage_heatmap(
    advantage_matrix,
    count_matrix
):

    values = advantage_matrix.to_numpy()

    fig, ax = plt.subplots(
        figsize=(11, 7)
    )

    heatmap = ax.imshow(
        values,
        aspect="auto"
    )

    ax.set_xticks(
        range(len(advantage_matrix.columns))
    )

    ax.set_xticklabels(
        advantage_matrix.columns,
        rotation=45,
        ha="right"
    )

    ax.set_yticks(
        range(len(advantage_matrix.index))
    )

    ax.set_yticklabels(
        advantage_matrix.index
    )

    ax.set_xlabel(
        "Discount to Analyst Consensus"
    )

    ax.set_ylabel(
        "Prior 5-Day Return"
    )

    ax.set_title(
        "Probability Advantage vs Same-Week S&P Stock Baseline"
    )

    for row in range(values.shape[0]):

        for col in range(values.shape[1]):

            value = values[row, col]

            if pd.notna(value):

                count = int(
                    count_matrix.iloc[row, col]
                )

                ax.text(
                    col,
                    row,
                    f"{value:+.2f} pp\n"
                    f"n={count:,}",
                    ha="center",
                    va="center"
                )

    colorbar = fig.colorbar(
        heatmap,
        ax=ax
    )

    colorbar.set_label(
        "Probability Advantage (Percentage Points)"
    )

    plt.tight_layout()

    plt.savefig(
        "data/same_week_probability_advantage_heatmap.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()
def test_large_momentum_significance(df):
    """
    Test whether stocks with large positive prior-week returns
    are more or less likely to be positive next week than other
    eligible S&P 500 stocks during the same week.

    Tests:
        5% to 10% prior-week return
        >= 10% prior-week return

    The statistical observations are calendar weeks, not individual
    stocks.
    """

    data = df.copy()

    # Make sure required data exists
    data = data.dropna(
        subset=[
            "prior_5d_return",
            "next_5d_return"
        ]
    )

    # Was each stock positive the following week?
    data["next_week_positive"] = (
        data["next_5d_return"] > 0
    ).astype(int)

    # Calculate the overall positive rate for EVERY calendar week
    weekly_baseline = (
        data.groupby("signal_date")["next_week_positive"]
        .mean()
        .rename("baseline_positive_rate")
    )

    groups = {
        "5% to 10%": (
            (data["prior_5d_return"] >= 0.05)
            &
            (data["prior_5d_return"] < 0.10)
        ),

        ">= 10%": (
            data["prior_5d_return"] >= 0.10
        )
    }

    results = []

    for group_name, condition in groups.items():

        group_data = data[condition].copy()

        # For each calendar week, find what percentage of
        # stocks in this momentum group went up next week
        weekly_signal = (
            group_data
            .groupby("signal_date")["next_week_positive"]
            .agg(
                signal_positive_rate="mean",
                stock_count="size"
            )
        )

        # Attach that week's overall market baseline
        weekly = weekly_signal.join(
            weekly_baseline,
            how="inner"
        )

        # Difference in probability for each week
        weekly["advantage"] = (
            weekly["signal_positive_rate"]
            -
            weekly["baseline_positive_rate"]
        )

        effects = weekly["advantage"]

        n_weeks = len(effects)

        mean_effect = effects.mean()

        std_effect = effects.std(ddof=1)

        standard_error = (
            std_effect / np.sqrt(n_weeks)
        )

        # 95% confidence interval
        critical_value = stats.t.ppf(
            0.975,
            df=n_weeks - 1
        )

        ci_low = (
            mean_effect
            -
            critical_value * standard_error
        )

        ci_high = (
            mean_effect
            +
            critical_value * standard_error
        )

        # Test H0: mean effect = 0
        t_statistic, p_value = stats.ttest_1samp(
            effects,
            popmean=0
        )

        results.append({
            "momentum_group": group_name,
            "weeks": n_weeks,
            "stock_observations": len(group_data),
            "average_advantage_pp": mean_effect * 100,
            "ci_low_pp": ci_low * 100,
            "ci_high_pp": ci_high * 100,
            "t_statistic": t_statistic,
            "p_value": p_value
        })

    results = pd.DataFrame(results)

    print("\n==============================================")
    print("LARGE MOMENTUM SIGNIFICANCE TEST")
    print("==============================================")

    for _, row in results.iterrows():

        print(
            f"\nPrior-week return: {row['momentum_group']}"
        )

        print(
            f"Weeks tested: {int(row['weeks']):,}"
        )

        print(
            f"Stock observations: "
            f"{int(row['stock_observations']):,}"
        )

        print(
            f"Average same-week probability advantage: "
            f"{row['average_advantage_pp']:+.2f} pp"
        )

        print(
            f"95% confidence interval: "
            f"[{row['ci_low_pp']:+.2f}, "
            f"{row['ci_high_pp']:+.2f}] pp"
        )

        print(
            f"t-statistic: {row['t_statistic']:.2f}"
        )

        print(
            f"p-value: {row['p_value']:.4f}"
        )

        if row["p_value"] < 0.05:

            if row["average_advantage_pp"] < 0:
                print(
                    "Result: statistically significant "
                    "evidence of reversal."
                )
            else:
                print(
                    "Result: statistically significant "
                    "evidence of continuation."
                )

        else:
            print(
                "Result: not statistically significant."
            )

    return results
def create_final_momentum_summary(df):
    """
    Create the final summary figure showing whether different levels
    of prior-week momentum predict next-week continuation or reversal
    relative to stocks trading during the same weeks.
    """

    data = df.copy()

    data = data.dropna(
        subset=[
            "prior_5d_return",
            "next_5d_return"
        ]
    )

    # Define momentum buckets
    momentum_bins = [
        -float("inf"),
        0,
        0.01,
        0.03,
        0.05,
        0.10,
        float("inf")
    ]

    momentum_labels = [
        "< 0%",
        "0% to 1%",
        "1% to 3%",
        "3% to 5%",
        "5% to 10%",
        ">= 10%"
    ]

    data["momentum_bucket"] = pd.cut(
        data["prior_5d_return"],
        bins=momentum_bins,
        labels=momentum_labels,
        right=False
    )

    # 1 = positive following week
    data["next_week_positive"] = (
        data["next_5d_return"] > 0
    ).astype(int)

    # Calculate baseline probability for each calendar week
    weekly_baseline = (
        data
        .groupby("signal_date")["next_week_positive"]
        .mean()
        .rename("baseline_positive_rate")
    )

    # Calculate each momentum bucket's probability
    # within each calendar week
    weekly_bucket = (
        data
        .groupby(
            ["signal_date", "momentum_bucket"],
            observed=True
        )
        .agg(
            bucket_positive_rate=(
                "next_week_positive",
                "mean"
            ),
            stock_count=(
                "next_week_positive",
                "size"
            )
        )
        .reset_index()
    )

    # Add the corresponding same-week baseline
    weekly_bucket = weekly_bucket.merge(
        weekly_baseline,
        on="signal_date",
        how="left"
    )

    # Difference relative to stocks in the same week
    weekly_bucket["advantage"] = (
        weekly_bucket["bucket_positive_rate"]
        -
        weekly_bucket["baseline_positive_rate"]
    )

    # Final result for each momentum bucket
    summary = (
        weekly_bucket
        .groupby(
            "momentum_bucket",
            observed=True
        )
        .agg(
            average_advantage=("advantage", "mean"),
            weeks=("signal_date", "nunique"),
            observations=("stock_count", "sum")
        )
        .reset_index()
    )

    summary["advantage_pp"] = (
        summary["average_advantage"] * 100
    )

    print("\n========================================")
    print("FINAL MOMENTUM SUMMARY")
    print("========================================")

    print(
        summary[
            [
                "momentum_bucket",
                "advantage_pp",
                "observations",
                "weeks"
            ]
        ].to_string(index=False)
    )

    # ---------- GRAPH ----------

    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    bars = ax.bar(
        summary["momentum_bucket"].astype(str),
        summary["advantage_pp"]
    )

    # Zero line
    ax.axhline(
        0,
        linewidth=1
    )

    ax.set_xlabel(
        "Prior 5-Day Stock Return"
    )

    ax.set_ylabel(
        "Next-Week Probability Advantage (Percentage Points)"
    )

    ax.set_title(
        "Does Weekly Momentum Continue or Reverse?"
    )

    # Put values and observation counts on bars
    # Add labels with enough distance from the bars
    for bar, (_, row) in zip(
        bars,
        summary.iterrows()
    ):

        value = row["advantage_pp"]
        count = int(row["observations"])

        if value >= 0:
            label_y = value + 0.12
            va = "bottom"
        else:
            label_y = value - 0.12
            va = "top"

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            label_y,
            f"{value:+.2f} pp\nn={count:,}",
            ha="center",
            va=va,
            fontsize=9
        )
    ax.set_ylim(
        summary["advantage_pp"].min() - 0.6,
        summary["advantage_pp"].max() + 0.6
    )
    plt.tight_layout()

    plt.savefig(
        "results/final_momentum_summary.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()

    # Save underlying results
    summary.to_csv(
        "results/final_momentum_summary.csv",
        index=False
    )

    return summary

def main():

    print("Loading weekly CRSP data...")
    crsp = load_crsp(
        CRSP_FILE
    )

    print(
        "CRSP weekly observations:",
        f"{len(crsp):,}"
    )

    print("\nLoading analyst consensus...")
    analysts = load_analyst_consensus(
        ANALYST_FILE
    )

    print(
        "Analyst weekly observations:",
        f"{len(analysts):,}"
    )

    print("\nCreating research panel...")

    panel = create_research_panel(
        crsp,
        analysts
    )

    print(
        "Merged observations:",
        f"{len(panel):,}"
    )

    print(
        "Observations with analyst consensus:",
        f"{panel['consensus_target'].notna().sum():,}"
    )

    # ------------------------------------------
    # FIRST LARGE-SCALE HYPOTHESIS TEST
    # ------------------------------------------

    test_positive_momentum_and_undervaluation(
        panel,
        discount_threshold=0.20,
        momentum_threshold=0.00,
        minimum_analysts=3
    )

    print("\nBuilding momentum x discount analysis...")

    bucketed = add_analysis_buckets(
        panel
    )

    matrix_results = build_momentum_discount_matrix(
        bucketed
    )

    (
    probability_matrix,
    return_matrix,
    excess_matrix,
    count_matrix
    ) = print_matrices(
        matrix_results
    )

    matrix_results.to_csv(
        "data/momentum_discount_matrix_results.csv",
        index=False
    )

    create_probability_heatmap(
        probability_matrix
    )

    print(
        "\nSaved matrix results and heatmap."
    )
    print(
    "\nCalculating same-week cross-sectional baseline..."
    )

    same_week_panel = add_same_week_baseline(
        panel,
        min_analysts=3
    )

    significance_results = test_large_momentum_significance(
        same_week_panel
    )

    significance_results.to_csv(
        "data/large_momentum_significance.csv",
        index=False
    )

    same_week_results = build_same_week_comparison(
        same_week_panel
    )

    advantage_matrix = print_same_week_comparison(
        same_week_results
    )

    create_same_week_advantage_heatmap(
        advantage_matrix,
        count_matrix
    )

    same_week_results.to_csv(
        "data/same_week_probability_comparison.csv",
        index=False
    )
    final_momentum_summary = create_final_momentum_summary(
        same_week_panel
    )


if __name__ == "__main__":
    main()