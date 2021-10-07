from model import Neighbourhood
from urllib.request import Request, urlopen
import json
import sqlite3
from pyproj import Geod
from shapely.ops import transform
import math
import pyproj
from shapely.geometry import Polygon


OUTDOOR_PAR_PER_POINT = 0.5

INDOOR_PAR_PER_POINT = 0.25

HOUSE_PAR_PER_POINT = 0.3

OVERPASS_URL = "http://localhost/api/interpreter"


def calculate(session):
    locations = session.query(Neighbourhood)
    for location in locations:
        haschilds = location_has_child(location)
        location.HasChilds = haschilds
        session.commit()
        places = get_places(location)
        house_area = sum(places[0].values())
        indoor_area = sum(places[1].values())
        outdoor_area = sum(places[2].values())
        par = (house_area * HOUSE_PAR_PER_POINT + indoor_area * INDOOR_PAR_PER_POINT +
               outdoor_area * OUTDOOR_PAR_PER_POINT) / sum(tuple((house_area, indoor_area, outdoor_area)))
        location.Ratio = par
        session.commit()


def postjson(url: str, body: str) -> dict:
    req = Request(url, data=body.encode(), method="POST")
    req.add_header("User-Agent", "CovidAlerter/1")
    respu = urlopen(req)
    resp = respu.read().decode()
    resdic = json.loads(resp)
    return resdic


def location_has_child(loc: Neighbourhood) -> bool:
    id = loc.OSMId
    osm_type = loc.OSMType
    query = f"[out:json];wr(area:{id})[boundary=administrative] -> .all;{osm_type}({str(int(id) - 3600000000) if osm_type == 'relation' else str(int(id) - 2400000000)}) -> .remove;(.all; - .remove;);out count;"
    resdic = postjson(OVERPASS_URL, query)
    haschilds = int(resdic["elements"][0]["tags"]["total"]) > 0
    return haschilds


def get_places(loc: Neighbourhood) -> tuple:
    if not loc.HasChilds:
        parks = get_parks(loc)
        for id in parks["polys"].keys():
            parks["polys"][id] = simplify(parks[id])
        homes = get_homes(loc)
        sh = homes["shops"]
        parks, homes, sh = cleanup(parks, homes, sh, parks["polys"])
        commercials = get_commercials(loc, sh)
        for id, points in parks.items():
            parks[id] = calculate_area(points)
        for id, points in homes.items():
            homes[id] = calculate_area(points)
        for id, points in commercials.items():
            commercials[id] = calculate_area(points)
        return (homes, commercials, parks)


def get_homes(loc: Neighbourhood) -> dict:
    id = loc.OSMId
    homes = {}
    query = f"[out:json];way(area:{id})[building~'^yes$|^residential$|^house$|^terrace$|^detached$|^apartments$'][!amenity][!shop][!office][!parking][!healthcare][!sport][!religion][!bridge][!phone][!fee][!tourism][!website][!leisure][!opening_hours][!email][!club][!shelter][!golf][!tennis][!historic] -> .ways; .ways map_to_area -> .wayareas;node(area.wayareas)[~\"^amenity$|^shop$|^lesire$|^website$|^email$|^club$|^opening_hours$|^shelter$|^office$|^parking$|^healthcare$|^sport$|^religion$|^fee$|^tourism$|^historic$|^tennis$\"~\".\"] -> .filternodes;.filternodes is_in -> .filternodesareas;area.filternodesareas[building=yes](if: t[\"building:levels\"] < 2) -> .filterways;(.ways; - way(pivot.filterways);) -> .mainways;.mainways out geom skel;"
    resdic = postjson(OVERPASS_URL, query)
    query = f'[out:json];node(area:{id})[~"^amenity$|^shop$|^leisure$|^website$|^email$|^club$|^opening_hours$|^shelter$|^office$|^parking$|^healthcare$|^sport$|^religion$|^fee$|^tourism$|^historic$|^tennis$"~"."]; out skel;'
    res = postjson(OVERPASS_URL, query)
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE nodes (id integer primary key, lat double, lon double)")
    conn.commit()
    for node in res["elements"]:
        cur.execute("INSERT INTO nodes VALUES (?, ?, ?)", [
                    node["id"], node["lat"], node["lon"]])
    conn.commit()
    shops = {}
    for elem in resdic["elements"]:
        geoms = []
        if len(cur.execute("SELECT id FROM nodes WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?", [elem["bounds"]["minlat"], elem["bounds"]["maxlat"], elem["bounds"]["minlon"], elem["bounds"]["maxlon"]]).fetchmany(5)) > 0:
            for geom in elem["geometry"]:
                geoms.append((geom['lon'], geom['lat']))
                shops[elem["id"]] = geoms
            continue
        for geom in elem["geometry"]:
            geoms.append((geom['lon'], geom['lat']))
        homes[elem["id"]] = geoms
    homes["shops"] = shops
    return homes


def get_commercials(loc: Neighbourhood, shops: dict) -> dict:
    id = loc.OSMId
    commercials = {}
    query = f'[out:json];way(area:{id})[building~"yes$|^residential$|^house$|^terrace$|^detached$|^apartments"][!amenity][!shop][!office][!parking][!healthcare][!sport][!religion][!bridge][!phone][!fee][!tourism][!website][!leisure][!opening_hours][!email][!club][!shelter][!golf][!tennis][!historic] -> .ways; .ways map_to_area -> .wayareas;node(area.wayareas)[~"amenity$|^shop$|^lesire$|^website$|^email$|^club$|^opening_hours$|^shelter$|^office$|^parking$|^healthcare$|^sport$|^religion$|^fee$|^tourism$|^historic$|^tennis"~"."] -> .filternodes;.filternodes is_in -> .filternodesareas;area.filternodesareas[building=yes](if: t["building:levels"] < 2) -> .filterways;(.ways; - way(pivot.filterways);) -> .homeways; (way(area:{id})[building]; - .homeways;) -> .commercials;.commercials out geom skel;'
    resdic = postjson(OVERPASS_URL, query)
    for elem in resdic["elements"]:
        geoms = []
        for geom in elem["geometry"]:
            geoms.append((geom['lon'], geom['lat']))
        commercials[elem["id"]] = geoms
    commercials.update(shops)
    return commercials


def get_parks(loc: Neighbourhood) -> dict:
    id = loc.OSMId
    parks = {}
    polystrs = {}
    query = f'[out:json];way(area:{id})[!building][leisure~"^park$|^beach_resort$|^dog_park$|^fishing$|^garden$|^marina$|^golf_course$|^miniature_golf$|^nature_reserve$|^outdoor_seating$|^pitch$|^playground$|^resort$|^slipway$|^sports_centre$|^sports_center$|^stadium$|^summer_camp$|^swimming_area$|^track$|^picinc$|^picnic_site$"] -> .leisures;way(area:{id})[!building][!boundary][area=yes][~"^highway$|^footway$"~"."] -> .areayes;way(area:{id})[!building][place~"^farm$|^square$"] -> .places;way(area:{id})[!building][tourism~"^camp_pitch$|^camp_site$|^caravan_site$|^picnic_site$|^theme_park$|^zoo$"] -> .tourisms;way(area:{id})[!building][landuse~"^$allotments|^farmland$|^farmyard$|^flowerbed$|^forest$|^meadow$|^orcahrd$|^vineyard$|^aquaculture$|^basin$|^resevoir$|^salt_pond$|^grass$|^greenfield|^plant_nursery$|^recreation_ground$|^religious$|^village_green$|^winter_sports$"] -> .landuses;way(area:{id})[!building][natural] -> .naturals;(.leisures; .areayes; .places; .tourisms; .landuses; .naturals;) -> .all;.all out geom skel;'
    resdic = postjson(OVERPASS_URL, query)
    for elem in resdic["elements"]:
        geoms = []
        polystr = ""
        for geom in elem["geometry"]:
            geoms.append((geom['lon'], geom['lat']))
            polystr += f"{geom['lat']} {geom['lon']} "
        polystrs[elem["id"]] = polystr[0:-1]
        parks[elem["id"]] = geoms
    parks["polys"] = polystrs
    return parks


def cleanup(p, h, s, polys: dict) -> dict:
    parks = p
    homes = h
    shops = s
    query = "[out:json];("
    keys = list(polys.keys())
    values = list(polys.values())
    for i in range(len(polys.values())):
        query += f"(way(poly:'{values[i]}'); - way({keys[i]}););"
    query += ") -> .all;"
    query += ".all out skel geom;"
    query = query.replace("\"", "").replace(",", ";")
    res = postjson(OVERPASS_URL, query)
    for childelem in res["elements"]:
        childid = childelem["id"]
        if childid in parks.keys():
            del parks[childid]
        if childid in homes.keys():
            del homes[childid]
            g = []
            for ge in childelem["geometry"]:
                g.append((ge['lon'], ge['lat']))
            shops[childid] = g
    del homes["shops"]
    del parks["polys"]
    return parks, homes, shops


def calculate_area(points) -> int:
    geod = Geod(ellps="WGS84")
    poly = Polygon(points)
    area = abs(geod.geometry_area_perimeter(poly)[0])
    return round(area)


def simplify(points) -> str:
    poly = Polygon(points)
    wgs84 = pyproj.CRS('EPSG:4326')
    utm = pyproj.CRS(
        'EPSG:' + convert_wgs_to_utm(poly.exterior.coords.xy[0][0], poly.exterior.coords.xy[1][0]))
    project = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True).transform
    deproject = pyproj.Transformer.from_crs(
        utm, wgs84, always_xy=True).transform
    utm_poly = transform(project, poly)
    simplified_utm_poly = utm_poly.simplify(5)
    simplified_poly = transform(deproject, simplified_utm_poly)
    result = ""
    for i in range(len(simplified_poly.exterior.coords.xy[0])):
        result += f"{simplified_poly.exterior.coords.xy[1][i]} {simplified_poly.exterior.coords.xy[0][i]} "
    result = result[:-1]
    return result


def convert_wgs_to_utm(lon: float, lat: float):
    utm_band = str((math.floor((lon + 180) / 6) % 60) + 1)
    if len(utm_band) == 1:
        utm_band = '0'+utm_band
    if lat >= 0:
        epsg_code = '326' + utm_band
        return epsg_code
    epsg_code = '327' + utm_band
    return epsg_code
