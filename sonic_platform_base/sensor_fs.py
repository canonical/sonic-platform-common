"""
    sensor_fs.py

    File system based sensors implementation. 
"""

from sonic_platform_base.sensor_base import SensorBase
from sonic_platform_base.sensor_base import VoltageSensorBase
from sonic_platform_base.sensor_base import CurrentSensorBase
import logging


class SensorFs(SensorBase):
    """Implementation of file system based sensor class"""

    __defaults = {
        'name': '',
        'sensor': '',
        'high_thresholds': ['N/A', 'N/A', 'N/A'],
        'low_thresholds': ['N/A', 'N/A', 'N/A'],
        'position': -1,
    }

    def __init__(self, sensor_type='sensor', **kw):

        super(SensorFs, self).__init__()

        if 'sensor' not in kw:
            raise Exception('Failed to initialize sensor')

        for k,v in self.__defaults.items():
            setattr(self, k, kw.get(k,v))

        if (len(self.high_thresholds) != 3 or len(self.low_thresholds) != 3):
            raise Exception('{}: Missing sensor thresholds'.format(self.name))

        self.minimum_sensor = self.get_value()
        self.maximum_sensor = self.minimum_sensor

    def get_name(self):
        """Returns the sensor name"""
        return self.name

    def get_value(self):
        """Returns the sensor measurement"""
        try:
            with open(self.sensor) as f:
                return int(f.readline().rstrip())
        except:
            return None

    def get_high_threshold(self):
        """Returns the sensor high threshold value"""
        return self.high_thresholds[1]

    def get_low_threshold(self):
        """Returns the sensor low threshold value"""
        return self.low_thresholds[1]

    def set_high_threshold(self, voltage):
        """Sets the sensor high threshold value"""
        self.high_thresholds[1] = voltage
        return True

    def set_low_threshold(self, voltage):
        """Sets the sensor low threshold value"""
        self.low_thresholds[1] = voltage
        return True

    def get_high_critical_threshold(self):
        """Returns the sensor critical high threshold value"""
        return self.high_thresholds[2]

    def get_low_critical_threshold(self):
        """Returns the sensor critical low threshold value"""
        return self.low_thresholds[2]

    def get_minimum_recorded(self):
        """Retrieves the minimum recorded sensor measurement"""
        tmp = self.get_value()
        if tmp is None:
            return None
        if tmp < self.minimum_sensor:
            self.minimum_sensor = tmp
        return self.minimum_sensor

    def get_maximum_recorded(self):
        """Retrieves the maximum recorded sensor measurement"""
        tmp = self.get_value()
        if tmp is None:
            return None
        if tmp > self.maximum_sensor:
            self.maximum_sensor = tmp
        return self.maximum_sensor

    def get_position_in_parent(self):
        """Retrieves 1-based relative physical position in parent device"""
        return self.position


class VoltageSensorFs(SensorFs, VoltageSensorBase):
    """File system based voltage sensor class"""

    DEVICE_TYPE = "voltage_sensor"

    def __init__(self, **kw):
        super(VoltageSensorFs, self).__init__(self.DEVICE_TYPE, **kw)

    @staticmethod
    def factory(sensors_data):
        """Factory method for retrieving a list of VoltageSensor objects"""
        logging.basicConfig()
        logger = logging.getLogger()

        result = []

        for idx, vsensor in enumerate(sensors_data):
            vsensor['position'] = idx + 1
            try:
                result.append(VoltageSensorFs(**vsensor))
            except Exception as e:
                logger.warning('Sensor.factory: {}'.format(e))

        return result

class CurrentSensorFs(SensorFs, CurrentSensorBase):
    """File systems based Current sensor class"""

    DEVICE_TYPE = "current_sensor"

    def __init__(self, **kw):
        super(CurrentSensorFs, self).__init__(self.DEVICE_TYPE, **kw)

    @staticmethod
    def factory(sensors_data):
        """Factory method for retrieving a list of CurrentSensor objects"""
        logging.basicConfig()
        logger = logging.getLogger()

        result = []

        for idx, csensor in enumerate(sensors_data):
            csensor['position'] = idx + 1
            try:
                result.append(CurrentSensorFs(**csensor))
            except Exception as e:
                logger.warning('Sensor.factory: {}'.format(e))

        return result
