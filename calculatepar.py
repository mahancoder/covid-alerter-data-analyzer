"""Required functions to calculate the Person-Area Ratio for each of the Neighbourhoods"""
import json
import psycopg2
import sqlalchemy
from sqlalchemy.orm.session import Session
from model import Base, Neighbourhood


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
    Base.metadata.create_all(bind=session.get_bind())
    # Get All stored neighbourhoods from the database
    locations = session.query(Neighbourhood)

    for location in locations:
        # Check if the location has any smaller administrative divisions
        location.HasChilds = check_location_childs(location, session)
        session.commit()
        # Calculate the PAR for the location
        if location.IsBig is False:
            # Get all the places
            location.Ratio = calculate_par(location)
        session.commit()

def calculate_par(loc: Neighbourhood) -> float:
    """Calculate the Person-Area Ratio for the specified location"""
    outdoor_area = get_outdoors(loc)
    house_area = get_indoors(loc)[0]
    commercial_area = get_indoors(loc)[1]
    par = ( OUTDOOR_PAR_PER_POINT * outdoor_area +
            INDOOR_PAR_PER_POINT * commercial_area +
            HOUSE_PAR_PER_POINT * house_area
          ) / (outdoor_area + commercial_area + house_area)
    return par

def get_indoors(loc: Neighbourhood) -> tuple:
    """Get the sum of all indoor places' area in a neighbourhood (houses_area, commercial_area)"""
    osm_id = loc.OSMId
    query = (
        # Select all the buildings inside the specified location
        "WITH all_buildings AS ( "
            "SELECT * "
            "FROM planet_osm_polygon AS place "
            "WHERE "
                # The place is inside our neighbourhood
                "ST_Within(place.way, "
                    "("
                        "SELECT way FROM planet_osm_polygon WHERE osm_id = %s"
                    ")"
                ") "
                # And the place is a building
                "AND place.building IS NOT NULL "
        "), "
        "houses AS ( "
            # Select all the houses inside the neighbourhood
            "SELECT house.osm_id, house.way_area "
            "FROM all_buildings AS house "
            # List generated by github copilot
            "WHERE house.building ~"
                "'^house$|"
                "^apartment$|"
                "^detached$|"
                "^semidetached$|"
                "^terraced$|^"
                "condominium$|"
                "^dormitory$|"
                "^bungalow$|"
                "^chalet$|"
                "^cabin$|"
                "^cottage$|"
                "^duplex$|"
                "^flat$|"
                "^houseboat$|"
                "^hut$|"
                "^maisonette$|"
                "^mansion$|"
                "^mews$|"
                "^mobile_home$|"
                "^semidetached_house$|"
                "^terraced_house$|"
                "^retirement_home$|"
                "^town_house$|"
                "^villa$|"
                "^yurt$' "
            "OR "
                "( "
                    # In OSM, some shops are mapped as a building with "building=yes" tag, and
                    # a node inside them with more information about the shop.
                    # Check for shop nodes inside the building
                    "SELECT COUNT(node.osm_id) FROM planet_osm_point AS node "
                    "WHERE "
                        "ST_Within(node.way, house.way) "
                        "AND "
                        "( "
                            "node.amenity IS NOT NULL "
                            "OR "
                            "node.shop IS NOT NULL "
                            "OR "
                            "node.leisure IS NOT NULL "
                            "OR "
                            "node.office IS NOT NULL "
                            "OR "
                            "node.tourism IS NOT NULL "
                            "OR "
                            "node.sport IS NOT NULL "
                            "OR "
                            "node.religion IS NOT NULL "
                            "OR "
                            "node.historic IS NOT NULL "
                        ") "
                ") = 0 "
        "), "
        "commercials AS ( "
            # Select all the commercial buildings inside the neighbourhood
            # Any building that is not a house is a commercial building
            "SELECT commercial.osm_id, commercial.way_area "
            "FROM all_buildings AS commercial "
            "WHERE commercial.osm_id NOT IN (SELECT houses.osm_id FROM houses) "
        ") "
        
        "SELECT SUM(houses.way_area), SUM(commercials.way_area) FROM houses, commercials"
    )

    # Run the query and return the result
    cur.execute(query, (osm_id, ))
    result = cur.fetchone()
    return result or 0

def get_outdoors(loc: Neighbourhood) -> float:
    """Get the sum all outdoor places' area in a neighbourhood"""
    osm_id = loc.OSMId

    query = (
        # Declare a temp table for the parents, to then calculate the sum from it
        "WITH parents AS ( "
            # Declare a temp table for the results with duplicates on having childs
            "WITH duplicated_results AS ( "
            # Declare a temp table for the results
                "WITH results AS ( "

                    # Select all the locations that are inside our neighbourhood
                    "SELECT child.osm_id as osm_id, child.way_area as way_area, child.way as way "
                    "FROM planet_osm_polygon AS child "
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

                        "("
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
                                # Anything that has the natural tag
                                "child.natural IS NOT NULL"
                            ")"

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

                # Filter out ways that are inside another way
                # (eg. playground inside a sorrounding park)

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
            "SELECT DISTINCT ON (parent_id) parent_area FROM duplicated_results "
            "WHERE parent_id NOT IN "
            "( "
                "SELECT child_id FROM duplicated_results WHERE child_id IS NOT NULL"
            ") "
        ") "

        "SELECT SUM(parents.parent_area) FROM parents"
    )

    # Run the query and return the result
    cur.execute(query, (osm_id, ))
    result = cur.fetchone()
    return result[0] or 0


def check_location_childs(loc: Neighbourhood, db_session: sqlalchemy.orm.session.Session) -> bool:
    """Returns True if the specified location has smaller administrative divisions inside"""
    osm_id = loc.OSMId

    query = (
        # Select the number of smaller divisions that are inside our location
        "SELECT child.name, child.osm_id, child.place FROM planet_osm_polygon AS child "
        "INNER JOIN planet_osm_polygon AS parent "
        "ON ST_Within(child.way, parent.way) "
        # Only childs which are administrative divisions (can be expanded for more tags)
        "WHERE ("
        "child.place='neighbourhood' OR child.place='county' OR child.place='municipality' "
        "OR child.boundary='administrative' OR child.boundary='postal_code'"
        ") "
        "AND "
        "parent.osm_id = %s "
        "AND "
        # Filter out the parent from the results
        "child.osm_id!=parent.osm_id "
        "AND "
        "child.way_area!=parent.way_area"
    )

    haschilds: bool

    # Run the query and return the result
    cur.execute(query, (osm_id, ))
    result = cur.fetchall()
    if len(result) > 0:
        for row in result:
            child = Neighbourhood(Name=row[0], OSMId=str(row[1]),
                                  IsRelation=str(row[1]).startswith('-'),
                                  LiveCount=0, IsBig=(row[2] is None))
            child.HasChilds = check_location_childs(child, db_session)
            if child.IsBig is False:
                child.Ratio = calculate_par(child)
            loc.Childs.append(child)
        haschilds = True
    else:
        loc.Childs = []
        haschilds = False
    return haschilds
