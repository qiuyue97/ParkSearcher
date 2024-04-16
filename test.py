import requests
import configparser


config = configparser.ConfigParser()
config.read('ak_config.ini')
ak = config['ak']['ak']

params = {
    "ak": ak,
    "output": "json",
    "coordtype": "wgs84",
    "extensions_poi": "1",
    "radius": "1000",
    "location": "31.322814,121.627179",
}
response = requests.get(url="https://api.map.baidu.com/reverse_geocoding/v3", params=params)
if response.json()['status'] == 0:
    print(response.json()['result']['addressComponent']['city'])
    yq_pois = [poi for poi in response.json()['result']['pois'] if '园区' in poi['tag']]
    for poi in yq_pois:
        print(poi['uid'])
