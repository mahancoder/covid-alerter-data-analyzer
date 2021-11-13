"""Analyze the reports to generate scores for each neighbourhood"""

import time
import json
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import calculatepar


def main():
    """The main function"""

    # Get start time for benchmarking
    start_time = time.time()

    # Get the database password
    db_password = json.load("password.json")["main"]

    # Connect to the database
    engine = sqlalchemy.create_engine(
        f"mysql://root:{db_password}@localhost:3306/CovidAlerter")
    session = sessionmaker(bind=engine)
    session = session()

    # Calculate the PAR
    calculatepar.calculate(session)

    # Get the execution time
    print("Time (ms): " + str((time.time() - start_time) * 1000))
    input("Press any key to exit...")


if __name__ == "__main__":
    main()
