import os
from datetime import datetime
import requests
import dotenv
import json
import argparse
import time
from influxdb import InfluxDBClient
from enum import Enum

class ReportType(Enum):
    CURRENT = 1
    FORECAST = 2
    DAILY = 3
    WEEKLY = 4

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
        elif self.type == ReportType.WEEKLY:
            measurement = 'weekly_weather'
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

def getDailyForecastData(cnt = 7) -> list:
    print('Getting forecast data from openweathermap for {} days'.format(cnt))
    API_FORECAST_URL='{}forecast/daily?lat={}&lon={}&appid={}&cnt={}&units={}&lang={}'.format(API_BASE_URL, LAT, LON, API_KEY, cnt, UNITS, LANG)    
    results = []
    try:
        response = requests.get(API_FORECAST_URL)
        # create the report        
        if response.status_code == 200:
            res = response.json()
            city = res['city']
            # retrieve list of forecast data
            forecasts = res['list']
            for forecast in forecasts:
                if (cnt == 1):
                    weather = WeatherReport(ReportType.DAILY)
                elif ((cnt > 1) and (cnt < 7)):
                    weather = WeatherReport(ReportType.FORECAST)
                elif (cnt == 7):
                    weather = WeatherReport(ReportType.WEEKLY)
                else:
                    print('Error: invalid cnt value')
                    return None

                # set location and coords
                weather.location = city['name']
                weather.coords = city['coord']
                weather.data['date'] = datetime.fromtimestamp(int(forecast['dt'])).strftime("%Y-%m-%d") # convert unix timestamp to date as string
                weather.data['sunrise'] = datetime.fromtimestamp(int(forecast['sunrise'])).strftime("%H:%M") # convert unix timestamp to time as string
                weather.data['sunset'] = datetime.fromtimestamp(int(forecast['sunset'])).strftime("%H:%M") # convert unix timestamp to time as string

                # collect general weather data
                weather_desc = forecast['weather'][0]
                weather.data['weather'] = weather_desc['main']
                weather.data['weather description'] = weather_desc['description']
                weather.data['weather icon'] = weather_desc['icon']
                
                # collect temp data
                weather.data['temp morning'] = forecast['temp']['morn']
                weather.data['felt temp morning'] = forecast['feels_like']['morn']
                weather.data['temp day'] = forecast['temp']['day']
                weather.data['felt temp day'] = forecast['feels_like']['day']
                weather.data['temp evening'] = forecast['temp']['eve']
                weather.data['felt temp evening'] = forecast['feels_like']['eve']
                weather.data['temp night'] = forecast['temp']['night']
                weather.data['felt temp night'] = forecast['feels_like']['night']
                weather.data['temp min'] = forecast['temp']['min']
                weather.data['temp max'] = forecast['temp']['max']
                
                # collect other data
                weather.data['pressure'] = forecast['pressure']
                weather.data['humidity'] = forecast['humidity']
                weather.data['cloud coverage'] = forecast['clouds']
                weather.data['wind speed'] = forecast['speed']
                weather.data['wind deg'] = forecast['deg']
                weather.data['wind gust'] = forecast['gust']
                weather.data['pop'] = int(forecast['pop']*100) # convert to percent

                # collect rain data
                if 'rain' in forecast:
                    weather.data['rain volume'] = forecast['rain']
                if 'snow' in forecast:
                    weather.data['snow volume'] = forecast['snow']

                results.append(weather)
        else:
            print('Error: {}, response: {}'.format(response.status_code, response.content))
        return results            
    except Exception as e:
        print('Error: {}'.format(e))
        return None

if __name__ == "__main__":

    # read args
    parser = argparse.ArgumentParser(description='Get weather data from openweathermap and write it to influxdb')
    parser.add_argument('-c', '--current', action='store_true', help='get current weather data')
    parser.add_argument('-f', '--forecast', action='store_true', help='get forecast weather data')
    parser.add_argument('-d', '--daily', action='store_true', help='get daily weather data')
    parser.add_argument('-n', '--numdays', type=int, default=7, help='number of days to get forecast data for')
    parser.add_argument('--ignore_db', action='store_true', default=False, help="don't write to influxdb, good for testing")
    
    args = parser.parse_args()
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
        todays_forecast = getDailyForecastData(cnt=1)[0] # get only the first day
        if todays_forecast.is_valid() and db_available:
            todays_forecast.write_to_influxdb(CLIENT)
        elif db_available == False:
            print('Error: influxdb is not available')
        else:
            print('Invalid daily weather report!')
    
    if args.forecast:
        if args.numdays > 1 and args.numdays <= 16:
            # get daily forecast data
            forecast_list = getDailyForecastData(args.numdays)
            for forecast in forecast_list:
                if forecast.is_valid() and db_available:
                    forecast.write_to_influxdb(CLIENT)
                    time.sleep(0.1) # wait 0.1 ms between writes to influxdb to avoid duplicate entries
                elif db_available == False:
                    print('Error: influxdb is not available')
                else:
                    print('Invalid forecast weather report!')
        else:
            print('Error: invalid number of days, choose between 1 and 16')