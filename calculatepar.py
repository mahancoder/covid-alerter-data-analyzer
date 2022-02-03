"""Required functions to calculate the Person-Area Ratio for each of the Neighbourhoods"""
import json
import psycopg2
from model import Neighbourhood
from sqlalchemy.orm.session import Session

# PAR ratio constants
OUTDOOR_PAR_PER_POINT = 0.5

INDOOR_PAR_PER_POINT = 0.25

HOUSE_PAR_PER_POINT = 0.3

# OSM Postgre Database Connection
with open("password.json", encoding="ascii") as file:
    osm_db_password = json.load(file)["osm"]
pgconn = psycopg2.connect(host="localhost", database="osm",
                          user="mahan", password=osm_db_password)

# OSM Postgre Database Cursor object
cur = pgconn.cursor()


def calculate(session: Session):
    """Calculate the Person-Area Ratio for each of the Neighbourhoods"""

    # Get All stored neighbourhoods from the database
    locations = session.query(Neighbourhood)

    for location in locations:
        # Check if the location has any smaller administrative divisions
        haschilds = location_has_child(location)
        location.HasChilds = haschilds
        session.commit()

        # TODO: Add calculation code
        get_outdoors(location)
        session.commit()


def get_outdoors(loc: Neighbourhood) -> tuple:
    """Get a list of all ourdoor locations in a neighbourhood"""
    osm_id = loc.OSMId

    query = (
        # Declare a temp table for the results with duplicates on having childs
        "WITH duplicated_results AS ( "
            # Declare a temp table for the results
            "WITH results AS ( "

                # Select all the locations that are inside our neighbourhood
                "SELECT child.osm_id as osm_id, child.way_area as way_area, child.way as way FROM planet_osm_polygon AS child "
                "INNER JOIN planet_osm_polygon AS parent "
                "ON ST_Within(child.way, parent.way) "

                "WHERE "
                "("
                    # The child is not a building or boundary
                    "("
                        "child.building IS NULL "
                        "AND "
                        "child.boundary IS NULL " 
                    ") "

                    "AND "

                    # The leisure tag
                    "("
                        "child.leisure ~ "
                            "'^park$|"
                            "^beach_resort$|"
                            "^dog_park$|"
                            "^fishing$|"
                            "^garden$|"
                            "^marina$|"
                            "^golf_course$|"
                            "^miniature_golf$|"
                            "^nature_reserve$|"
                            "^outdoor_seating$|"
                            "^pitch$|"
                            "^playground$|"
                            "^resort$|"
                            "^slipway$|"
                            "^sports_centre$|"
                            "^sports_center$|"
                            "^stadium$|"
                            "^summer_camp$|"
                            "^swimming_area$|"
                            "^track$|^picinc$|"
                            "^picnic_site$'"
                    ")"

                    "OR "

                    # The area tag
                    "("
                        "child.area='yes'"
                    ")"

                    "OR "

                    # The place tag
                    "("
                        "child.place ~ "
                        "'^farm$|"
                        "^square$'"
                    ")"

                    "OR "

                    # The tourism tag
                    "("
                        "child.tourism ~ "
                        "'^camp_pitch$|"
                        "^camp_site$|"
                        "^caravan_site$|"
                        "^picnic_site$|"
                        "^theme_park$|"
                        "^zoo$'"
                    ")"

                    "OR "

                    # The landuse tag
                    "("
                        "child.landuse ~ "
                        "'^$allotments|"
                        "^farmland$|"
                        "^farmyard$|"
                        "^flowerbed$|"
                        "^forest$|"
                        "^meadow$|"
                        "^orcahrd$|"
                        "^vineyard$|"
                        "^aquaculture$|"
                        "^basin$|"
                        "^resevoir$|"
                        "^salt_pond$"
                        "|^grass$|"
                        "^greenfield|"
                        "^plant_nursery$|"
                        "^recreation_ground$|"
                        "^religious$|"
                        "^village_green$|"
                        "^winter_sports$'"
                    ")"

                    "OR "

                    # The natureal tag
                    "("
                        #Anything that has the natural tag
                        "child.natural IS NOT NULL"
                    ")"
                ")"
                # Specify the neighbourhood id
                "AND "
                "parent.osm_id = %s "

                "AND "

                # Filter out the parent from the results
                "child.osm_id!=parent.osm_id "
                "AND "
                "child.way_area!=parent.way_area"
            ") "

            # Filter out ways that are inside another way (eg. playground inside a sorrounding park)

            # Store parents and childs in the temp table
            "SELECT parent.osm_id AS parent_id, "
                "child.osm_id AS child_id, "
                "parent.way_area AS parent_area "
            "FROM results AS parent "
            "LEFT JOIN results AS child "
                "ON ( "
                    "ST_Within(child.way, parent.way) "
                    "AND child.osm_id!=parent.osm_id "
                    "AND child.way_area!=parent.way_area "
                ") "
        ") "

        # Select parents that are not in the childs list (that are not childs of anything else)
        "SELECT DISTINCT ON (parent_id) parent_area FROM duplicated_results WHERE parent_id NOT IN "
        "( "
            "SELECT child_id FROM duplicated_results WHERE child_id IS NOT NULL"
        ") "
    )

    # Convert Area Id to PostGis OSM Id format
    query_id = int(osm_id) - 2400000000 if loc.OSMType == "way" else - \
        (int(osm_id) - 3600000000)

    # Run the query and return the result
    cur.execute(query, (query_id, ))
    result = cur.fetchall()
    return result


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
