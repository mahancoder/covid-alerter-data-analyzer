"""Analyze the reports to generate scores for each neighbourhood"""

import time
import json
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import calculate_par
import calculate_scores
from model import Base


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
    Base.metadata.create_all(engine)

    # Calculate the PAR
    calculate_par.calculate(session)

    # Calculate the score
    calculate_scores.calculate(session)

    # Print the benchmarking time
    print(f"--- {time.time() - start_time} seconds ---")


if __name__ == "__main__":
    main()
