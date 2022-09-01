import os
from datetime import datetime
import requests
import dotenv
import json
from influxdb import InfluxDBClient
from enum import Enum

class ReportType(Enum):
    CURRENT = 1
    FORECAST = 2

class Direction(Enum):
    N = 1
    NNE = 2
    NE = 3
    ENE = 4
    E = 5
    ESE = 6
    SE = 7
    SSE = 8
    S = 9
    SSW = 10
    SW = 11
    WSW = 12
    W = 13
    WNW = 14
    NW = 15
    NNW = 16

BASEPATH = os.path.dirname(os.path.abspath(__file__))

url="http://localhost:8086"

env = dotenv.load_dotenv()
LAT = os.getenv('LAT')
LON = os.getenv('LON')
API_KEY = os.getenv('API_KEY')
UNITS = 'metric'
LANG = 'de'
API_URL='https://api.openweathermap.org/data/2.5/weather?lat={}&lon={}&appid={}&units={}&lang={}'.format(LAT, LON, API_KEY, UNITS, LANG)

CLIENT = InfluxDBClient(host=os.getenv('INFLUXDB_HOST'),
                        port=os.getenv('INFLUXDB_PORT'),
                        username=os.getenv('INFLUXDB_USER'),
                        password=os.getenv('INFLUXDB_PASSWORD'),
                        database=os.getenv('INFLUXDB_DATABASE'))

class WeatherReport:
    def __init__(self, type: ReportType):
        self.timestamp = datetime.now()
        self.location = None
        self.coords = {'lat': None, 'lon': None}
        self.type = type
        self.data = {}

    def __str__(self):
        return json.dumps(self.data, indent=4, sort_keys=True, ensure_ascii=False)
    
    def write_to_influxdb(self):
        if self.type == ReportType.CURRENT:
            measurement = 'current_weather'
        elif self.type == ReportType.FORECAST:
            measurement = 'forecast_weather'
        report_data = [
            {'measurement': measurement,
                'tags': {'location': self.location},
                'time': self.timestamp,
                'fields': self.data
            }
        ]
        CLIENT.write_points(report_data)

    def is_valid(self):
        if self.data['temperature'] is None:
            return False
        else:
            return True

def getCurrentData() -> WeatherReport:
    print('Getting data from openweathermap')
    try:
        response = requests.get(API_URL)
        # create the report
        weather = WeatherReport(ReportType.CURRENT)
        if response.status_code == 200:
            res = response.json()
            
            # set location and coords
            weather.location = res['name']
            weather.coords['lat'] = res['coord']['lat']
            weather.coords['lon'] = res['coord']['lon']

            # weather description (first in list)
            weather_desc = res['weather'][0]
            weather.data['weather'] = weather_desc['main']
            weather.data['weather description'] = weather_desc['description']

            # main data
            main = res['main']
            weather.data['temperature'] = main['temp']
            weather.data['temperature min'] = main['temp_min']
            weather.data['temperature max'] = main['temp_max']
            weather.data['felt temp'] = main['feels_like']
            weather.data['humidity'] = main['humidity']
            weather.data['pressure'] = main['pressure']
            weather.data['visibility'] = res['visibility']
            weather.data['cloud coverage'] = res['clouds']['all']
            
            # wind speed and direction
            wind = res['wind']
            weather.data['wind speed'] = wind['speed']
            weather.data['wind deg'] = wind['deg']

            # sunrise and sunset
            tz_shift = int(res['timezone'])
            print('tz_shift: {}'.format(tz_shift))
            weather.data['sunrise'] = datetime.utcfromtimestamp(int(res['sys']['sunrise'] + tz_shift)).strftime('%H:%M:%S')
            weather.data['sunset'] = datetime.utcfromtimestamp(int(res['sys']['sunset'] + tz_shift)).strftime('%H:%M:%S')

            if 'rain' in res:
                weather.data['rain next hour'] = res['rain']['1h']
                weather.data['rain next 3 hours'] = res['rain']['3h'] 
            if 'snow' in res:
                weather.data['snow next hour'] = res['snow']['1h']
                weather.data['snow next 3 hours'] = res['snow']['3h']
        else:
            print('Error: {}, response: {}'.format(response.status_code, response.content))
        return weather
    except Exception as e:
        print('Error: {}'.format(e))
        return None

if __name__ == "__main__":
    current_weather = getCurrentData()
    print(current_weather)
    if current_weather.is_valid():
        current_weather.write_to_influxdb()
    else:
        print('Invalid weather report')
    
    # TODO implement forecast data