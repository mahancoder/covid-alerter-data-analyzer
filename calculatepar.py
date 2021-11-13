"""Requires functions to calculate the Person-Area Ratio for each of the Neighbourhoods"""
import json
import psycopg2
from model import Neighbourhood

# PAR ratio constants
OUTDOOR_PAR_PER_POINT = 0.5

INDOOR_PAR_PER_POINT = 0.25

HOUSE_PAR_PER_POINT = 0.3

# OSM Postgre Database Connection
with open("password.json", encoding="ascii") as file:
    osm_db_password = json.load(file)["osm"]
pgconn = psycopg2.connect(host="localhost", database="osm",
                          user="postgres", password=osm_db_password)

# OSM Postgre Database Cursor object
cur = pgconn.cursor()


def calculate(session):
    """Calculate the Person-Area Ratio for each of the Neighbourhoods"""

    # Get All stored neighbourhoods from the database
    locations = session.query(Neighbourhood)

    for location in locations:
        # Check if the location has any smaller administrative divisions
        haschilds = location_has_child(location)
        location.HasChilds = haschilds
        session.commit()

        # TODO: Add calculation code
        session.commit()


def location_has_child(loc: Neighbourhood) -> bool:
    """Returns True if the specified location has smaller administrative divisions inside"""
    osm_id = loc.OSMId

    query = (
        # Select the number of smaller divisions that are inside our location
        "SELECT COUNT(child.osm_id) FROM planet_osm_polygon AS child "
        "INNER JOIN planet_osm_polygon AS parent "
        "ON ST_Within(child.way, parent.way) "
        # Only childs which are administrative divisions (can be expanded for more tags)
        "WHERE (child.place='neighbourhood' OR child.boundary='administrative') "
        "AND "
        "parent.osm_id = %s "
        "AND "
        # Filter out the parent from the results
        "child.osm_id!=parent.osm_id "
        "AND "
        "child.way_area!=parent.way_area"
    )

    # Convert Area Id to PostGis OSM Id format
    query_id = int(osm_id) - 2400000000 if loc.OSMType == "way" else - \
        (int(osm_id) - 3600000000)

    # Run the query and return the result
    cur.execute(query, (query_id, ))
    result = cur.fetchone()
    haschilds = result[0] > 0
    return haschilds
