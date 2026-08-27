import wrds


def main():

    conn = wrds.Connection()

    link = conn.raw_sql("""
        SELECT
            ticker,
            permno,
            ncusip,
            sdate,
            edate,
            score
        FROM wrdsapps_link_crsp_ibes.ibcrsphist
        WHERE edate >= '2005-01-01'
          AND sdate <= '2025-12-31'
        ORDER BY ticker, sdate
    """, date_cols=["sdate", "edate"])

    print("\n===== I/B/E/S ↔ CRSP LINK TABLE =====")
    print("Rows:", len(link))
    print("Unique I/B/E/S tickers:", link["ticker"].nunique())
    print("Unique PERMNOs:", link["permno"].nunique())

    print("\nScore distribution:")
    print(link["score"].value_counts(dropna=False).sort_index())

    print("\nSample:")
    print(link.head(20))

    link.to_csv(
        "data/ibes_crsp_link_2005_2025.csv",
        index=False
    )

    print("\nSaved to data/ibes_crsp_link_2005_2025.csv")

    conn.close()


if __name__ == "__main__":
    main()