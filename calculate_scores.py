"""Required functions to find the stays longer than the threshold"""
from datetime import datetime
from sqlalchemy.orm.session import Session

from model import ScoreLog

# The number of hours that count as a stay, stays less than this will be ignored
THRESHOLD_MINUTES = 60
# The report collection rate (how often are reports generated)
REPORT_MINUTES = 15
# The number of consecutive reports needed to be considered a stay
CONSECUTIVE_COUNT = (THRESHOLD_MINUTES / REPORT_MINUTES) - 1
# TODO: Add the functionailty to change consecutive count in the query based on this constant

def calculate(session: Session) -> tuple:
    """Find the stays"""
    query = (
        "SELECT results.NeighbourhoodId, "
        # Round to 2 decimal points
        "ROUND ( "
            # The number of stays multipled by the neighbourhood ratio
            "SUM(results.ReportCount) * neighbourhood.Ratio"
        ", 2) "
        "AS Score "
        "FROM ( "
            # Select the neighbourhood,
            "SELECT DISTINCT windowed_reports.NeighbourhoodId, "
            # And the number of stay reports
            "ROUND("
                "POWER("
                    "COUNT(*) OVER (PARTITION BY UserId, NeighbourhoodId"
                ") - 3, 0.25"
            ") + 1, 2) AS ReportCount "
            "FROM ("
            # Run a window function to get the required columns,
            # next timestamp, and previous timestamp of a report neighbouhoods
            "SELECT "
                "Id, UserId, NeighbourhoodId, Timestamp, "
                "LEAD(NeighbourhoodId) OVER (PARTITION BY UserId ORDER BY Timestamp) "
                    "AS next_neighbourhood,"
                "LEAD(NeighbourhoodId, 2) OVER (PARTITION BY UserId ORDER BY Timestamp) "
                    "AS second_next_neighbourhood, "
                "LAG(NeighbourhoodId) OVER (PARTITION BY UserId ORDER BY Timestamp) "
                    "AS prev_neighbourhood, "
                "LAG(NeighbourhoodId, 2) OVER (PARTITION BY UserId ORDER BY Timestamp) "
                    "AS second_prev_neighbourhood, "
                "LEAD(Timestamp) OVER (PARTITION BY UserId ORDER BY Timestamp) "
                    "AS next_timestamp, "
                "LAG(Timestamp) OVER (PARTITION BY UserId ORDER BY Timestamp) "
                    "AS prev_timestamp "
            "FROM CovidAlerter.Reports"
            ") AS windowed_reports "
            "WHERE "
                # The report is the start of a stay
                "("
                    "windowed_reports.NeighbourhoodId = windowed_reports.next_neighbourhood "
                    "AND "
                    "windowed_reports.NeighbourhoodId = windowed_reports.second_next_neighbourhood"
                ") "
                "OR "
                # The report is in the middle of a stay
                "("
                    "windowed_reports.NeighbourhoodId = windowed_reports.next_neighbourhood "
                    "AND "
                    "windowed_reports.NeighbourhoodId = windowed_reports.prev_neighbourhood"
                ") "
                "OR "
                # The report is the end of a stay
                "("
                    "windowed_reports.NeighbourhoodId = windowed_reports.prev_neighbourhood "
                    "AND "
                    "windowed_reports.NeighbourhoodId = windowed_reports.second_prev_neighbourhood"
                ") "
        ") AS results "
        # Join the neighbourhood to get the ratio
        "INNER JOIN CovidAlerter.Neighbourhoods AS neighbourhood "
        "ON results.NeighbourhoodId = neighbourhood.Id "
        "GROUP BY results.NeighbourhoodId"
        ";"
    )
    results = session.execute(query).fetchall()
    # Result row format:
    # (NeighbourhoodId, Score)

    # Create a table row for each neighbourhood
    logs = [ScoreLog(NeighbourhoodId=result[0], Score=result[1],
                    Date=datetime.utcnow().date()) for result in results]

    # Add the scores and commit to table
    session.add_all(logs)
    session.commit()
