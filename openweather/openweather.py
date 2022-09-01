import os
from datetime import datetime
import requests
import dotenv
import json
import argparse
from influxdb import InfluxDBClient
from enum import Enum

class ReportType(Enum):
    CURRENT = 1
    FORECAST = 2
    DAILY = 3

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
API_BASE_URL = 'http://api.openweathermap.org/data/2.5/'

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
    
    def write_to_influxdb(self, client):
        if self.type == ReportType.CURRENT:
            measurement = 'current_weather'
        elif self.type == ReportType.FORECAST:
            measurement = 'forecast_weather'
        elif self.type == ReportType.DAILY:
            measurement = 'today_weather'
        report_data = [
            {'measurement': measurement,
                'tags': {'location': self.location},
                'time': self.timestamp,
                'fields': self.data
            }
        ]
        client.write_points(report_data)
        

    # TODO improve validity check
    def is_valid(self):
        if self.location is None:
            return False
        else:
            return True

def getCurrentData() -> WeatherReport:
    print('Getting data from openweathermap')
    API_CURRENT_URL='{}weather?lat={}&lon={}&appid={}&units={}&lang={}'.format(API_BASE_URL, LAT, LON, API_KEY, UNITS, LANG)
    try:
        response = requests.get(API_CURRENT_URL)
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
            weather.data['weather icon'] = weather_desc['icon']

            # main data
            main = res['main']
            weather.data['temperature'] = main['temp']
            weather.data['felt temp'] = main['feels_like']
            weather.data['humidity'] = main['humidity']
            weather.data['pressure'] = main['pressure']
            weather.data['visibility'] = res['visibility']
            weather.data['cloud coverage'] = res['clouds']['all']
            
            # wind speed and direction
            wind = res['wind']
            weather.data['wind speed'] = wind['speed']
            weather.data['wind deg'] = wind['deg']

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

def getDailyForecastData(cnt:int = 5) -> WeatherReport:
    print('Getting forecast data from openweathermap for {} days'.format(cnt))
    API_FORECAST_URL='{}forecast/daily?lat={}&lon={}&appid={}&cnt={}&units={}&lang={}'.format(API_BASE_URL, LAT, LON, API_KEY, cnt, UNITS, LANG)    
    try:
        response = requests.get(API_FORECAST_URL)
        # create the report
        
        if response.status_code == 200:
            res = response.json()
            city = res['city']

            # retrieve list of forecast data
            forecasts = res['list']
            for forecast in forecasts:
                if cnt == 1:
                    weather = WeatherReport(ReportType.DAILY)
                elif cnt > 1:
                    weather = WeatherReport(ReportType.FORECAST)
                else:
                    print('Error: invalid cnt value')
                    return None
                # set location and coords
                weather.location = city['name']
                weather.coords = city['coord']
                weather.data['date'] = datetime.fromtimestamp(int(forecast['dt'])).strftime("%Y-%m-%d") # convert unix timestamp to date as string
                
        else:
            print('Error: {}, response: {}'.format(response.status_code, response.content))
        return weather
    except Exception as e:
        print('Error: {}'.format(e))
        return None

if __name__ == "__main__":

    # read args
    parser = argparse.ArgumentParser(description='Get weather data from openweathermap and write it to influxdb')
    parser.add_argument('-c', '--current', action='store_true', help='get current weather data')
    parser.add_argument('-f', '--forecast', action='store_true', help='get forecast weather data')
    parser.add_argument('-d', '--daily', action='store_true', help='get daily weather data')
    parser.add_argument('-n', '--numdays', type=int, default=5, help='number of days to get forecast data for')
    parser.add_argument('--ignore_db', action='store_true', default=False, help="don't write to influxdb, good for testing")
    
    args = parser.parse_args()
    print(args)

    # init db connection
    db_available = False

    if not args.ignore_db:
        try:
            CLIENT.ping()
            db_available = True
        except Exception as e:
            print('Error: {}'.format(e))

    # get current weather data
    if args.current:
        current_weather = getCurrentData()
        if current_weather.is_valid() and db_available:
            current_weather.write_to_influxdb(CLIENT)
        elif db_available == False:
            print('Error: influxdb is not available')
        else:
            print('Invalid current weather report!')
    
    # todays forecast data
    if args.daily:
        todays_forecast = getDailyForecastData(cnt=1)
        if todays_forecast.is_valid() and db_available:
            todays_forecast.write_to_influxdb(CLIENT)
        elif db_available == False:
            print('Error: influxdb is not available')
        else:
            print('Invalid daily weather report!')
    
    if args.forecast:
        if args.numdays > 1 and args.numdays <= 16:
            # get daily forecast data
            forecast_weather = getDailyForecastData()
            if forecast_weather.is_valid() and db_available:
                forecast_weather.write_to_influxdb(CLIENT)
            elif db_available == False:
                print('Error: influxdb is not available')
            else:    
                print('Invalid weather forecast report!')
        else:
            print('Error: invalid number of days, choose between 1 and 16')