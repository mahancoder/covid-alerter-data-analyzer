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
    with open("password.json", encoding="ascii") as file:
        db_password = json.load(file)["main"]

    # Connect to the database
    engine = sqlalchemy.create_engine(
        f"mysql://mahan:{db_password}@localhost:3306/CovidAlerter")

    # Create a session
    session: sqlalchemy.orm.session.Session = sessionmaker(bind=engine)()

    # Calculate the PAR
    calculatepar.calculate(session)

    # Get the execution time
    print("Time (ms): " + str((time.time() - start_time) * 1000))
    input("Press any key to exit...")


if __name__ == "__main__":
    main()
