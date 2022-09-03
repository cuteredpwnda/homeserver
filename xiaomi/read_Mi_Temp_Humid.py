import os
import time
from datetime import datetime, timezone
import glob
import subprocess
import dotenv
from influxdb import InfluxDBClient

BASEPATH = os.path.dirname(os.path.abspath(__file__))

url="http://localhost:8086"

env = dotenv.load_dotenv()

CLIENT = InfluxDBClient(host=os.getenv('INFLUXDB_HOST'),
                        port=os.getenv('INFLUXDB_PORT'),
                        username=os.getenv('INFLUXDB_USER'),
                        password=os.getenv('INFLUXDB_PASSWORD'),
                        database=os.getenv('INFLUXDB_DATABASE'))

def get_temperature(sensor):
    # Get temperature from sensor
    success = False
    retries = 0
    while not success:
        with subprocess.Popen(['sh', '{}/sensors/./{}'.format(BASEPATH, sensor)], stdout=subprocess.PIPE) as proc:
            while True:
                line = proc.stdout.readline().decode('utf-8').rstrip()
                print(line)
                if not line:
                    break
                if 'reading failed' in line or 'error' in line:
                    print('current retries: {}'.format(retries))
                    if retries >= 3:
                        print('Too many retries - giving up')
                        return
                    else:
                        retries += 1
                        print('Retrying, backing off for {} seconds'.format(2**retries))
                        time.sleep(1*2**retries)
                        break
                if  'busy' in line:
                    return
                else:
                    try:
                        l, t, h, b = line.rstrip().split(', ')
                    except Exception as e:
                        print('Something went wrong parsing line {} trying again.'.format(line))
                        break

                    # create object
                    output = SensorReading(l, t, h, b)
                    print('Got data: {}'.format(output))
                    if output.is_valid():
                        output.write_to_file()
                        output.write_to_influxdb()
                        success = True

class SensorReading:
    def __init__(self, location, temperature, humidity, battery):
        self.timestamp = datetime.now()
        self.location = str(location)
        self.temperature = float(temperature)
        self.humidity = int(humidity)
        self.battery = float(battery)

    def __str__(self):
        return '{}, {}, {}°C, {}%, {}V'.format(self.timestamp.strftime('%Y-%m-%dT%H:%M:%S'), self.location, self.temperature, self.humidity, self.battery)
    
    def write_to_file(self):
        path = os.path.join(BASEPATH, '../data/temperature.csv')
        if not os.path.exists(path):
            with open(path, 'w') as f:
                f.write('timestamp, location, temperature, humidity, battery\n')
        with open(path, 'a') as f:
            f.write('{}\n'.format(self))
    
    def write_to_influxdb(self):
        data = [
            {
                'measurement': 'temp_sensor',
                'tags': {
                    'location': self.location
                },
                'time': self.timestamp,
                'fields': {
                    'temperature': self.temperature,
                    'humidity': self.humidity,
                    'battery': self.battery
                }
            }
        ]
        CLIENT.write_points(data)

    def is_valid(self):
        if self.temperature > 60 or self.temperature < -10:
            return False
        if self.humidity > 100 or self.humidity < 0:
            return False
        if self.battery > 3.5 or self.battery < 2.5:
            return False
        return True

if __name__ == "__main__":
    sensors = [x.split('/')[-1] for x in glob.glob(BASEPATH + '/sensors/*Mi_Temp_Humid_*.sh')]
    for sensor in sensors:
        get_temperature(sensor)