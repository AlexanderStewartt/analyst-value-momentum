Purpose:
This project tests whether stocks trading at a discounted value relative to analyst price targets experience a stronger second weeks after a strong week prior. 

Input/Data used:
- CRSP daily stock prices and returns
- I/B/E/S individual analyst price targets

Current pipeline:
1. Calculates prior 5-trading-day returns.
2. Calculates subsequent 5-trading-day returns.
3. Samples one observation per stock per week.
4. Constructs a point-in-time analyst consensus using each analyst's most recent target published within the prior 30 days.
5. Equal-weights analysts.
6. Calculates the stock's discount to analyst consensus value.
7. Tests whether positive momentum combined with analyst-implied undervaluation predicts stronger subsequent returns.

Current exploritory values
(to qualify as undervalued/ having momentum):
- Prior 5-day momentum: >= 3%
- Discount to analyst consensus value: >= 20%
- Minimum analysts: 3
( completely arbitrary)

Biggest issues and planned improvements:
- Expand to more stocks( currently just 10 )
- reduce survivorship biase
- optimize analyst concensus construction as this is the biggest bottleneck

- add analyst target revisions

- analyze on more continuous spectra
  not just 20% undervalued, +3% momentum

- review where most instances are coming from as 15 of 40 instances occured in 2022. (Analyst price targets weren't updated)



Results from prototype:

Weekly observations: 3044
Weekly observations with analyst consensus: 2949

Saved research panel to: data/weekly_research_panel.csv

========================================
VALUE + MOMENTUM ANALYSIS
========================================

Momentum threshold: 3.0%
Discount threshold: 20.0%
Minimum analysts: 3

--- MOMENTUM + UNDERVALUED ---
Observations: 39
Positive next week: 43.59%
Average next-week return: -0.41%
Median next-week return: -1.41%

--- MOMENTUM BUT NOT UNDERVALUED ---
Observations: 607
Positive next week: 58.98%
Average next-week return: 0.71%
Median next-week return: 0.63%

--- DIFFERENCE ---
Increase in probability of positive next week: -15.39%
Difference in average next-week return: -1.12%

===== QUALIFYING OBSERVATIONS BY TICKER =====
ticker
NVDA     14
AMZN     12
GOOGL     5
META      4
MSFT      3
AAPL      2
dtype: int64

===== QUALIFYING OBSERVATIONS BY YEAR =====
year
2022    15
2023     8
2024     5
2025    12
dtype: int64

===== ACTUAL OBSERVATIONS =====
     ticker signal_date  ...  analyst_count  next_5d_return
125    MSFT  2022-05-27  ...           16.0       -0.016432
129    MSFT  2022-06-24  ...            6.0       -0.030333
944    AAPL  2022-06-24  ...            5.0       -0.019272
2231   AMZN  2022-06-24  ...            9.0       -0.059248
632    META  2022-07-08  ...            8.0       -0.036166
2233   AMZN  2022-07-08  ...            7.0       -0.017224
2235   AMZN  2022-07-22  ...           14.0        0.102352
636    META  2022-08-05  ...           39.0        0.080127
2874  GOOGL  2022-10-07  ...            6.0       -0.021484
2248   AMZN  2022-10-21  ...           10.0       -0.133339
2876  GOOGL  2022-10-21  ...           12.0       -0.047858
146    MSFT  2022-10-21  ...           16.0       -0.025812
650    META  2022-11-11  ...           41.0       -0.008581
2251   AMZN  2022-11-11  ...           36.0       -0.065979
2879  GOOGL  2022-11-11  ...           29.0        0.010580
2260   AMZN  2023-01-13  ...            7.0       -0.006117
2888  GOOGL  2023-01-13  ...            6.0        0.083262
2262   AMZN  2023-01-27  ...            8.0        0.011248
2895  GOOGL  2023-03-03  ...           22.0       -0.032247
2274   AMZN  2023-04-21  ...            5.0       -0.014118
2293   AMZN  2023-09-01  ...           38.0        0.036056
1011   AAPL  2023-10-06  ...            4.0        0.007662
2302   AMZN  2023-11-03  ...           18.0        0.035786
2328   AMZN  2024-05-03  ...           32.0        0.006820
2661   NVDA  2024-09-13  ...           29.0       -0.026028
2663   NVDA  2024-09-27  ...           26.0        0.028995
2665   NVDA  2024-10-11  ...            5.0        0.023738
2676   NVDA  2024-12-27  ...            6.0        0.090650
2677   NVDA  2025-01-03  ...            4.0       -0.077802
2682   NVDA  2025-02-07  ...            6.0        0.069394
2683   NVDA  2025-02-14  ...            5.0       -0.061723
2687   NVDA  2025-03-14  ...           22.0       -0.032630
2693   NVDA  2025-04-25  ...           16.0        0.031439
2699   NVDA  2025-06-06  ...           28.0        0.001834
2720   NVDA  2025-10-31  ...           12.0       -0.070819
2410   AMZN  2025-11-28  ...           48.0       -0.015822
809    META  2025-11-28  ...           39.0        0.039308
2725   NVDA  2025-12-05  ...           34.0       -0.040514
2727   NVDA  2025-12-19  ...           30.0        0.039948
2728   NVDA  2025-12-26  ...            5.0             NaN

[40 rows x 8 columns]