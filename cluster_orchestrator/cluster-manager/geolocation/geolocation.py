import ipaddress
import requests
from flask import request
import pandas as pd
import time
import numpy as np

df = None

def build_geolite_dataframe():
    global df
    print("Start building GeoLite2 dataframe...")
    start = time.time()
    chunk = pd.read_csv('geolocation/GeoLite2-City-Blocks-IPv4.csv', chunksize=500000,
                        usecols=['network', 'latitude', 'longitude'],
                        dtype={'network': 'str', 'latitude': np.float64, 'longitude': np.float64})
    df = pd.concat(chunk)
    end = time.time()
    print(f"...done building the dataframe. Took {end-start}s")

def query_geolocation_for_ips(ip_addresses):
    global df
    ip_addresses = [ipaddress.ip_address(ip) for ip in ip_addresses]
    ip_locations = {}
    for ip in ip_addresses:
        print(f"Lookup: {ip}")
        # If IP Adress is private just return artificial coordinates contained in url params or 0 if no params were given
        if ip.is_private:
            lat = request.args.get("lat") or 0
            long = request.args.get("long") or 0
            return {'lat': lat, 'long': long}

        # Get first byte of IP
        first_byte = str(ip).split(".")[0]

        # In case the first byte is not contained in the GeoLite2 database, keep decrementing the first byte and check if it exists
        start_idx = 0
        for i in range(int(first_byte), -1, -1):
            indices = df[df.network.str.startswith(f"{i}.")].index
            if len(indices) >= 1:
                start_idx = indices[0]
                print(f"Start lookup at index {start_idx}/{df['network'].size} with first byte {i}")
                break

        # Start at start_idx to reduce number of iterations
        for i in range(start_idx, df['network'].size):
            ip_network = ipaddress.ip_network(df.at[i, 'network'])
            if ip in ip_network:
                lat = df.at[i, 'latitude']
                long = df.at[i, 'longitude']
                ip_locations[str(ip)] = {"lat": lat, "long": long}
                print(f"Found coords: {lat},{long} for IP {str(ip)}")
                # Stop lookup when IP was found to avoid long running process
                break
    return ip_locations

def geolocate_ip_via_api():
    url = f"http://ip-api.com/json/{request.remote_addr}"
    resp = requests.get(url)
    data = resp.json()
    lat = data.get("lat")
    long = data.get("lon")

    return lat, long


def user_in_cluster(user, cluster):
    """
    Checks whether the 'user' is located within the cluster or its boundaries. Since shapely is coordinate-agnostic it
    will handle geographic coordinates expressed in latitudes and longitudes exactly the same way as coordinates on a
    Cartesian plane. But on a sphere the behavior is different and angles are not constant along a geodesic.
    For that reason we do a small distance correction here.
    """
    return True if cluster.intersects(user) or user.within(cluster) or cluster.distance(user) < 1e-5 else False
