# Analyst Value & Momentum --- Project Handoff

## Purpose

This document is a compact handoff for quickly reconstructing the
project in a future ChatGPT conversation.

The project is an empirical equity-research study testing whether
short-term stock momentum is more likely to continue when analyst
consensus price targets imply that the stock is undervalued.

### Original hypothesis

> Stocks with positive prior-week momentum should be more likely to
> continue rising in the following week when analyst consensus price
> targets imply substantial undervaluation.

The final analysis did **not** support this hypothesis consistently.
Instead, the strongest finding was evidence consistent with **short-term
mean reversion after large positive weekly returns**, particularly
prior-week gains of 5--10%.

------------------------------------------------------------------------

## Final Research Design

### Research period

Approximately **2005--2025**.

### Universe

Historical S&P 500 constituents rather than today's S&P 500 membership.

This was a deliberate change from the prototype to reduce **survivorship
bias**. A stock is eligible only when it was actually an S&P 500
constituent at the relevant historical date.

Historical membership was obtained from a third-party historical S&P 500
constituent CSV after the user's WRDS subscription was found not to
include CRSP index membership tables.

Membership validation produced approximately 500 constituents on
historical test dates, e.g.:

-   2005-01-03: 495
-   2008-09-15: 498
-   2010-01-04: 499
-   2015-01-02: 499
-   2020-01-02: 505
-   2025-01-02: 503

Small deviations from exactly 500 can occur because of membership
changes, multiple share classes, timing, etc.

------------------------------------------------------------------------

## Data Sources

### CRSP

Daily historical stock data for all relevant historical S&P 500
constituents.

Example raw structure:

``` text
PERMNO,HdrCUSIP,Ticker,PERMCO,IssuerNm,DlyCalDt,DlyPrc,DlyCap,DlyRet,sprtrn
10078,86681020,JAVA,8021,SUN MICROSYSTEMS INC,2007-08-27,5.140000,18182837.38,0.025948,-0.008504
```

Important identifier:

**PERMNO** is the primary stock identifier used by the research
pipeline.

This avoids relying on ticker symbols, which change through time.

### I/B/E/S

Historical individual analyst price-target data.

Example structure:

``` text
TICKER,OFTIC,CNAME,ACTDATS,ESTIMID,ALYSNAM,HORIZON,VALUE,ANNDATS
AT1,A,AGILENT,2020-01-07,FRCLAYSC,MEEHAN J,12,85,2020-01-07
```

The analysis uses **12-month analyst price targets**.

### CRSP ↔ I/B/E/S Link Table

WRDS table:

``` text
wrdsapps_link_crsp_ibes.ibcrsphist
```

Columns:

``` text
ticker
permno
ncusip
sdate
edate
score
```

The link is date-sensitive.

Downloaded link-table statistics included:

-   21,329 rows
-   14,929 unique I/B/E/S tickers
-   12,258 unique PERMNOs

High-quality links primarily used scores 1 and 2.

After filtering 12-month targets and linking I/B/E/S to CRSP:

-   Total target observations: 311,751 in an earlier partial dataset
-   Successful links: 254,250
-   Link success: 81.56%
-   Virtually all successful observations were score 1
-   Later, after correcting the I/B/E/S download to cover 2005--2025,
    linked analyst observations increased to **751,550**

------------------------------------------------------------------------

## Why PERMNO Matters

Do not merge long historical datasets primarily using ticker.

Ticker symbols change because of:

-   corporate renaming
-   mergers
-   reorganizations
-   ticker reassignment
-   share-class changes

The project therefore converts analyst observations to historical CRSP
**PERMNOs** using the WRDS CRSP/I/B/E/S link table and the effective
link dates.

This is an important methodological feature of the project.

------------------------------------------------------------------------

## Main Data Pipeline

The pipeline conceptually works as:

``` text
Historical S&P Membership
          ↓
CRSP Daily Stock Data
          ↓
Filter stocks by historical membership
          ↓
Create weekly stock observations
          ↓
I/B/E/S raw analyst targets
          ↓
Historical CRSP/I/B/E/S identifier linking
          ↓
Point-in-time weekly analyst consensus
          ↓
Merge consensus with weekly CRSP panel
          ↓
Momentum × valuation analysis
          ↓
Same-week cross-sectional benchmarking
          ↓
Statistical significance tests
```

------------------------------------------------------------------------

## Weekly CRSP Panel

The large CRSP dataset contained:

**3,732,280 daily rows**

After calculating returns and constructing weekly observations:

**774,491 weekly observations before S&P membership filtering**

After historical S&P membership filtering:

**532,420 weekly stock observations**

Other diagnostics:

-   948 unique PERMNOs
-   Date range: 2005-01-07 through 2025-12-31

Approximate annual observations were around 23,000--27,000 stock-weeks
per year.

Important weekly variables include:

``` text
permno
signal_date
prior_5d_return
next_5d_return
```

The signal is based on the **change in the stock price during the prior
week**, not on changes in analyst targets.

------------------------------------------------------------------------

## Analyst Consensus Construction

The analyst-consensus pipeline is deliberately **point-in-time**.

For each stock and weekly signal date:

1.  Consider analyst targets known by that date.
2.  Use targets within approximately the previous **30 days**.
3.  Keep the **most recent report from each analyst**.
4.  Do not allow one analyst with multiple reports to receive extra
    weight.
5.  Equal-weight the remaining analysts.
6.  Calculate the weekly consensus target.
7.  Record analyst count and dispersion.
8.  Calculate changes/revisions in consensus as additional diagnostic
    variables.

Important fields include:

``` text
consensus_target
analyst_count
target_std
previous_consensus
target_revision_1w
```

Although target revisions were calculated, the primary hypothesis is
based on **prior-week stock momentum and the level of analyst-implied
discount**, not changing analyst-estimate momentum.

### Final consensus diagnostics

Using the corrected 2005--2025 I/B/E/S dataset:

-   Linked analyst observations: 751,550
-   After analyst-update deduplication: 749,937
-   Candidate analyst-week rows: 4,499,622
-   Valid analyst-week matches: 2,422,658
-   Weekly stock observations: 532,420
-   Observations with analyst consensus: **461,583**
-   Coverage: **86.70%**
-   Unique PERMNOs with consensus: 927

Analyst count distribution:

-   mean: 5.25
-   median: 4
-   25th percentile: 2
-   75th percentile: 7
-   maximum: 50

The main tests generally require **at least 3 analysts**.

------------------------------------------------------------------------

## Original Simple Hypothesis Test

Initial final-scale test:

-   prior-week return \> 0%
-   analyst-implied undervaluation ≥20%
-   minimum analysts = 3

Results:

### Positive momentum + ≥20% undervalued

-   Observations: 14,172
-   Probability next week positive: 50.86%
-   Average next-week return: 0.021%
-   Median: 0.116%
-   Average S&P-adjusted return: 0.025%

### Positive momentum + \<20% undervalued

-   Observations: 153,714
-   Probability next week positive: 52.66%
-   Average next-week return: 0.137%
-   Median: 0.186%
-   Average S&P-adjusted return: 0.018%

Difference:

-   Probability: **−1.80 percentage points**
-   Average return: −0.115%
-   S&P-adjusted return: +0.007%

All positive-momentum observations had a 52.51% probability of being
positive the next week.

This provided little support for the original hypothesis.

------------------------------------------------------------------------

## Momentum × Analyst Discount Matrix

Momentum buckets:

``` text
< 0%
0% to 1%
1% to 3%
3% to 5%
5% to 10%
>= 10%
```

Analyst-discount buckets:

``` text
< 0%
0% to 10%
10% to 20%
20% to 30%
30% to 40%
>= 40%
```

A heatmap was created showing next-week positive probabilities, with
sample counts displayed for each cell.

The raw probabilities suggested that negative prior-week returns often
had relatively high next-week positive probabilities, while very large
prior-week gains had lower continuation probabilities.

However, unconditional probabilities can be misleading because market
conditions differ across historical periods.

------------------------------------------------------------------------

## Critical Benchmarking Improvement

The project therefore moved to a **same-week cross-sectional
benchmark**.

The preferred question became:

> During weeks when this signal occurred, were these stocks more or less
> likely to rise next week than the average eligible S&P 500 constituent
> available during the same week?

For every signal observation:

1.  Calculate the signal group's probability of a positive next week.
2.  Calculate the probability that eligible S&P constituents in that
    same historical week rose.
3.  Subtract the same-week baseline.

Thus:

``` text
probability advantage =
signal positive probability
− contemporaneous eligible-S&P-stock positive probability
```

This avoids comparing a narrow signal occurring during particular market
regimes with an unconditional 20-year market average.

Positive advantage = relative continuation.

Negative advantage = relative reversal.

------------------------------------------------------------------------

## Same-Week Heatmap Results

### Signal positive rate

  Momentum     \<0% discount   0--10%   10--20%   20--30%   30--40%   \>=40%
  ---------- --------------- -------- --------- --------- --------- --------
  \<0%                55.74%   53.99%    54.96%    54.18%    55.11%   53.44%
  0--1%               54.34%   53.52%    54.27%    54.29%    52.36%   48.56%
  1--3%               52.84%   52.66%    53.38%    52.22%    51.36%   50.73%
  3--5%               52.19%   52.33%    54.06%    51.56%    58.01%   45.97%
  5--10%              49.45%   51.52%    52.91%    52.47%    52.05%   47.42%
  \>=10%              46.06%   49.66%    47.96%    40.59%    44.72%   41.05%

### Advantage versus same-week S&P-stock baseline

  ----------------------------------------------------------------------------
  Momentum         \<0%     0--10%    10--20%    20--30%    30--40%     \>=40%
               discount                                             
  ---------- ---------- ---------- ---------- ---------- ---------- ----------
  \<0%         +1.46 pp   −0.14 pp   +0.31 pp   −0.70 pp   −0.79 pp   −1.80 pp

  0--1%        +1.25 pp   +0.68 pp   +0.69 pp   +1.21 pp   +0.68 pp   −4.00 pp

  1--3%        +0.33 pp   −0.02 pp   +0.05 pp   −0.69 pp   −1.50 pp   −1.43 pp

  3--5%        +0.26 pp   −0.05 pp   +0.51 pp   −1.82 pp   +2.67 pp   −0.88 pp

  5--10%        **−2.04    **−1.15    **−0.31    **−0.31    **−0.29    **−3.49
                   pp**       pp**       pp**       pp**       pp**       pp**

  \>=10%        **−2.20    **−0.92    **−2.36    **−6.15   +1.78 pp    **−2.32
                   pp**       pp**       pp**       pp**                  pp**
  ----------------------------------------------------------------------------

The most notable descriptive pattern is that the **5--10% prior-week
return row is negative across every analyst-valuation bucket**.

Analyst discount does not display a consistent monotonic relationship
with continuation probability.

This weakens the original analyst-undervaluation hypothesis.

------------------------------------------------------------------------

## Final Momentum Summary

For the final high-level figure, analyst-discount buckets were collapsed
and momentum alone was compared with contemporaneous eligible S&P
stocks.

Final results:

  Prior-week return     Probability advantage   Observations   Weeks
  ------------------- ----------------------- -------------- -------
  \<0%                              +0.449 pp        142,589   1,094
  0--1%                             +1.001 pp         37,810   1,091
  1--3%                             −0.274 pp         61,725   1,094
  3--5%                             −0.311 pp         33,402   1,080
  5--10%                        **−1.369 pp**         26,473   1,067
  \>=10%                        **−1.377 pp**          8,476     903

Interpretation:

-   Very small positive moves show slight continuation.
-   The relationship turns mildly negative around 1--5%.
-   Large positive weeks show the strongest descriptive reversal.
-   5--10% and \>=10% prior-week gains both show approximately −1.37 pp
    next-week probability advantage.

The final graph is saved as approximately:

``` text
results/final_momentum_summary.png
```

------------------------------------------------------------------------

## Statistical Significance Check

The final project intentionally did **not** become a large econometric
exercise.

Only the two most interesting large-positive-momentum groups were
tested:

-   5--10%

-   =10%

The statistical unit was the **calendar week**, not each individual
stock observation, because stocks observed in the same week are
correlated by common market conditions.

For each week:

``` text
weekly effect =
P(next week positive | momentum group)
−
P(next week positive | eligible stocks that week)
```

Then the average weekly effect and a 95% confidence interval were
calculated across historical weeks using a one-sample t-test against
zero.

### Results

  -------------------------------------------------------------------------------
  Prior-week            Stock        Weeks       Effect       95% CI      p-value
  return         observations                                        
  ------------ -------------- ------------ ------------ ------------ ------------
  5--10%               26,473        1,067 **−1.37 pp**   **\[−2.55,   **0.0234**
                                                           −0.19\]** 

  \>=10%                8,476          903     −1.38 pp     \[−3.44,       0.1911
                                                             +0.69\] 
  -------------------------------------------------------------------------------

### Interpretation

For the **5--10% group**, zero is outside the 95% confidence interval
and p \< 0.05.

Therefore:

> There is statistically significant evidence consistent with short-term
> reversal following prior-week gains of 5--10%.

Do **not** say the project "proved mean reversion."

For the **\>=10% group**, the point estimate is similarly negative, but
the confidence interval crosses zero and p = 0.1911.

Therefore:

> The \>=10% group points toward reversal descriptively, but there is
> insufficient statistical evidence to conclude that its true relative
> effect differs from zero.

The result CSV is approximately:

``` text
results/large_momentum_significance.csv
```

------------------------------------------------------------------------

## Final Conclusion

The original hypothesis was **not supported**.

The project began with the idea that analyst-implied undervaluation
might identify stocks whose positive weekly momentum was more likely to
continue.

After improving the research design:

-   historical S&P membership reduced survivorship bias;
-   historical PERMNO links reduced ticker-identity errors;
-   analyst targets were made point-in-time;
-   analysts were deduplicated and equally weighted;
-   signals were compared with stocks trading in the same historical
    weeks;
-   large-momentum results received a limited significance check.

Analyst-implied discount did **not** consistently strengthen momentum.

Instead, the strongest result was:

> Stocks gaining 5--10% in the prior week were about **1.37 percentage
> points less likely to rise the following week than contemporaneous
> eligible S&P 500 constituents**, and this difference was statistically
> significant at the 5% level (p = 0.0234).

This is evidence consistent with **short-term mean reversion**, not a
proven trading strategy.

------------------------------------------------------------------------

## Why the Project Is Valuable Despite the Failed Hypothesis

The research process is arguably more important than discovering a
profitable signal.

The project evolved roughly as follows:

``` text
Initial hypothesis
      ↓
Small prototype
      ↓
Larger historical dataset
      ↓
Historical S&P universe
      ↓
PERMNO-based identity matching
      ↓
Point-in-time analyst consensus
      ↓
Momentum × valuation matrix
      ↓
Recognition that unconditional baseline was misleading
      ↓
Same-week cross-sectional benchmark
      ↓
Original hypothesis weakens
      ↓
Evidence of large-move reversal emerges
      ↓
Focused statistical significance check
```

The analysis was allowed to reject the original idea rather than
changing the hypothesis until a desirable result appeared.

Avoid continuing to slice thresholds simply to obtain more significant
findings.

------------------------------------------------------------------------

## Important Limitations

1.  Analyst targets can respond slowly to rapid price changes, meaning
    apparent "undervaluation" may partly represent stale analyst
    information.
2.  Analyst coverage varies by firm and historical period.
3.  The study does not establish a causal mechanism for reversal.
4.  It is not a fully specified trading strategy.
5.  Transaction costs, bid/ask spreads, liquidity constraints, shorting
    constraints, taxes, and portfolio construction are not modeled.
6.  Statistical significance does not guarantee future or out-of-sample
    persistence.
7.  Firm characteristics, sector effects, earnings announcements,
    volatility, and other predictors are not explicitly controlled.
8.  Historical S&P membership came from a third-party constituent
    history because the available WRDS subscription did not include CRSP
    index membership access.
9.  Multiple exploratory cells were viewed in the heatmap; the final
    significance testing was intentionally limited rather than searching
    extensively for significant cells.

------------------------------------------------------------------------

## Suggested Repository Structure

``` text
analyst-value-momentum/
│
├── README.md
├── PROJECT_HANDOFF.md
├── requirements.txt
├── .gitignore
│
├── src/
│   ├── main.py
│   ├── build_weekly_crsp.py
│   ├── link_ibes_crsp.py
│   ├── build_analyst_consensus.py
│   └── other helper/download scripts
│
├── results/
│   ├── final_momentum_summary.png
│   ├── same_week_probability_advantage_heatmap.png
│   ├── final_momentum_summary.csv
│   └── large_momentum_significance.csv
│
└── data/
    └── local research data (generally gitignored)
```

Do **not** publicly redistribute large raw WRDS/CRSP/I/B/E/S datasets.

------------------------------------------------------------------------

## Python / Tools

Primary technologies:

-   Python
-   pandas
-   NumPy
-   SciPy
-   Matplotlib
-   WRDS Python package
-   CRSP
-   I/B/E/S
-   Git / GitHub

A virtual environment (`.venv`) was used.

The project encountered package-isolation issues where libraries
installed globally were not available inside `.venv`. Install packages
inside the active environment when necessary.

Before finalizing the repository:

``` powershell
pip freeze > requirements.txt
```

------------------------------------------------------------------------

## Git Notes

The project uses GitHub as a normal iterative development workflow.

Typical final update:

``` powershell
git status
git add .
git commit -m "Finalize momentum research analysis and results"
git push origin main
```

Raw data should be ignored using `.gitignore`, e.g.:

``` text
.venv/
__pycache__/
*.pyc
data/*.csv
```

Small derived result CSVs belong in `results/` and can be committed.

------------------------------------------------------------------------

## Final README Framing

Recommended project framing:

**Empirical asset-pricing / quantitative research project**, not "AI
stock predictor" or a proven trading strategy.

Concise summary:

> Tested whether analyst-implied undervaluation strengthens weekly stock
> momentum using historical S&P 500 membership, CRSP returns, and
> point-in-time I/B/E/S price targets from 2005--2025. After controlling
> for contemporaneous market conditions, analyst discount did not
> consistently improve momentum continuation. Large prior-week gains
> instead showed evidence of short-term reversal, with 5--10% weekly
> gainers 1.37 percentage points less likely to rise the following week
> relative to contemporaneous eligible S&P constituents (p=0.023).

Possible resume bullet:

> Analyzed 500K+ historical S&P 500 stock-week observations using
> Python, CRSP, and I/B/E/S; built a point-in-time analyst-consensus and
> survivorship-bias-aware research pipeline, finding statistically
> significant short-term reversal following 5--10% weekly gains
> (p=0.023).

------------------------------------------------------------------------

## If Resuming This Project Later

A future assistant should first inspect the current repository because
exact filenames/functions may differ from this handoff.

The key methodological rules to preserve are:

1.  **Use PERMNO, not ticker, as the durable historical security
    identity.**
2.  **Filter by historical S&P membership at the signal date.**
3.  **Never use analyst information that became available after the
    signal date.**
4.  **Use only the latest eligible target per analyst within the
    consensus window.**
5.  **Require an analyst-count threshold where appropriate (main
    analysis used 3).**
6.  **The hypothesis concerns prior stock-price momentum plus the level
    of analyst-implied discount---not analyst-target momentum.**
7.  **Prefer contemporaneous same-week cross-sectional benchmarks to
    unconditional 20-year averages.**
8.  **Treat the 5--10% reversal as evidence, not proof.**
9.  **The \>=10% reversal estimate was not statistically significant.**
10. **Do not keep searching thresholds merely to find significant
    results.**

The project was intentionally considered complete after: - focused
statistical significance testing, - a final momentum-summary
visualization, - README/documentation.
