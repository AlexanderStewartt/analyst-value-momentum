import wrds
"""
this file is used to connect CRSP stock ID to IBES ticker ID using the WRDS ibcrsphist table   
"""

def main():

    conn = wrds.Connection()

    print("\nColumns in wrdsapps_link_crsp_ibes.ibcrsphist:\n")

    description = conn.describe_table(
        library="wrdsapps_link_crsp_ibes",
        table="ibcrsphist"
    )

    print(description)

    conn.close()


if __name__ == "__main__":
    main()