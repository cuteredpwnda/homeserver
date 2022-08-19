import os
import time
from datetime import datetime
import glob
import subprocess
BASEPATH = os.path.dirname(os.path.abspath(__file__))

def get_temperature(sensor):
    # Get temperature from sensor
    success = False
    retries = 0
    while not success:
        with subprocess.Popen(['sh', '{}/./{}'.format(BASEPATH, sensor)], stdout=subprocess.PIPE) as proc:
            while True:
                line = proc.stdout.readline().decode('utf-8').rstrip()
                print(line)
                if not line:
                    break
                if 'reading failed' in line or 'error' in line:
                    print('current retries: {}'.format(retries))
                    if retries >= 5:
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
                        l, t, h = line.rstrip().split(', ')
                    except Exception as e:
                        print('Something went wrong parsing line {} trying again.'.format(line))
                        break

                    # create object
                    output = Temperature(l, t, h)
                    print('Got data: {}'.format(output))
                    if output.is_valid():
                        output.write_to_file()
                        success = True

class Temperature:
    def __init__(self, location, temperature, humidity):
        self.timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        self.location = str(location)
        self.temperature = float(temperature)
        self.humidity = int(humidity)

    def __str__(self):
        return '{}, {}, {}°C, {}%'.format(self.timestamp, self.location, self.temperature, self.humidity)
    
    def write_to_file(self):
        path = os.path.join(BASEPATH, '../data/temperature.csv')
        print(path)
        with open(path, 'a') as f:
            f.write('{}\n'.format(self))

    def is_valid(self):
        if self.temperature > 60 or self.temperature < -10:
            return False
        if self.humidity > 100 or self.humidity < 0:
            return False
        return True

if __name__ == "__main__":
    sensors = glob.glob(BASEPATH + '/sensors/*Mi_Temp_Humid_*.sh')
    print(sensors)
    #for sensor in sensors:
    #    get_temperature(sensor)