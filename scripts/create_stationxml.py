#!/usr/bin/python3
# Create a StationXML file describing the Yuma seismometer and digitizer
# response.
#
# Refer to:
# https://docs.fdsn.org/projects/stationxml/en/latest/response.html#broadband-sensor
# https://docs.obspy.org/tutorial/code_snippets/stationxml_file_from_scratch.html
# https://docs.obspy.org/packages/obspy.clients.nrl.html

import obspy
import cmath
import json
import math
from obspy.core.inventory import Inventory, Network, Station, Channel, Site
from obspy.core.inventory.util import Equipment
from obspy.core.inventory import InstrumentSensitivity, InstrumentPolynomial
from obspy.core.inventory import Response, ResponseStage
from obspy.core.inventory import PolesZerosResponseStage, CoefficientsTypeResponseStage
from obspy.core.inventory import PolynomialResponseStage
from obspy.clients.nrl import NRL
from scipy.signal import convolve

################################################################################
# The instrument response for Yuma2 seismometers.
# Since each Yuma2 is unique, call lookup() to lookup known parameters based on
# the serial number. Or, instantiate directly with specific parameters.
#
class Yuma2Response:
    # Known parameters for each serial number:
    config = {}
    config["1"] = {                             # serial number 1
        "generator_constant": 1344,             # volt-sec/meter
        "poles": [
            complex('-0.08498+8.433e-4j'),
            complex('-0.08498-8.433e-4j'),
            complex('-209.7+0j'),
            complex('-1000+0j'),
            complex('-1002632+0j') ],
        "zeros": [
            complex('0+0j'),
            complex('-4.181e-6+0j') ]
    }
    config["2"] = {                             # serial number 2
        "generator_constant": 844.5,
        "poles": [
            complex('-0.085842+8.651e-4j'),
            complex('-0.085842-8.651e-4j'),
            complex('-209.7+0j'),
            complex('-1000+0j'),
            complex('-1002632+0j') ],
        "zeros": [
            complex('0+0j'),
            complex('-4.181e-6+0j') ]
    }
    config["3"] = {                             # serial number 3
        "generator_constant": 1083,
        "poles": [
            complex('-0.08375+8.264e-4j'),
            complex('-0.08375-8.264e-4j'),
            complex('-209.7+0j'),
            complex('-1005+0j'),
            complex('-1000100+0j') ],
        "zeros": [
            complex('0+0j'),
            complex('-4.114e-6+0j') ],
    }

    # Usually not instantiated directly.  Use the lookup() method instead.
    def __init__(self, serial_number, generator_constant, poles, zeros):
        self.serial_number = serial_number
        self.normalization_frequency = 1.0
        self.pz_transfer_function_type = 'LAPLACE (RADIANS/SECOND)'
        self.response_stage = PolesZerosResponseStage(
            1,
            stage_gain = generator_constant,
            stage_gain_frequency = 1.0,
            input_units = 'M/S',
            output_units = 'V',
            pz_transfer_function_type = self.pz_transfer_function_type,
            normalization_frequency = self.normalization_frequency,
            normalization_factor =
                calc_normalization_factor(
                    poles, zeros, self.normalization_frequency,
                    self.pz_transfer_function_type),
            zeros = zeros,
            poles = poles,
            # Note: in StationXML file only the name of stage[0] is used.
            name = 'Yuma2 mechanical rev 4.3, electrical rev 4.0',
            input_units_description = 'Velocity in meters per second',
            output_units_description = 'Volts')

    def response(self):
        # Return the pole-zero response for the vertical channel.
        return self.response_stage

    def temperature_response(self):
        # Return the response for the temperature channel.
        # Linear output of 0.01V / deg C, from -55 to +150C
        return PolynomialResponseStage(
            1,
            stage_gain = 1.0,
            stage_gain_frequency = 1.0,
            input_units = 'degC',
            output_units = 'V',
            frequency_lower_bound = 0.001,
            frequency_upper_bound = 100,
            approximation_lower_bound = -55.0,
            approximation_upper_bound = 150.0,
            maximum_error = 0.5,    # in degrees?
            coefficients = [ 0, 0.01 ],
            # Note: in StationXML file only the name of stage[0] is used.
            name = 'Yuma2 mechanical rev 4.3, electrical rev 4.0',
            input_units_description = 'Degrees Centigrade',
            output_units_description = 'Volts')

    def __str__(self):
        return self.response_stage.__str__()

    @classmethod
    def lookup(cls, serial_number):
        if serial_number not in cls.config.keys():
            raise Exception("Serial number {} is unknown, no data available."
                .format(serial_number))
        # Create an instance for this serial number.
        data = cls.config[serial_number]
        return cls(serial_number, data['generator_constant'], data['poles'], data['zeros'])


################################################################################
# PSN-ADC24 digitizer response, in a single supported configuration:
# 4 channels, gain = 2, 100 Hz ODR
#
class PsnAdc24Response:

    def __init__(self, divider_ratio=1/17.0):
        self.stages = []

        # Stage 1: Digitizer input voltage divider and antialiasing filter.
        poles = [complex('-282.6+0j')]           # 45 Hz LPF
        zeros = []
        pz_transfer_function_type = 'LAPLACE (RADIANS/SECOND)'
        normalization_frequency = 1.0

        self.stages.append(PolesZerosResponseStage(
            len(self.stages)+1,
            stage_gain = divider_ratio,
            stage_gain_frequency = normalization_frequency,
            input_units = 'V',
            output_units = 'V',
            pz_transfer_function_type = pz_transfer_function_type,
            normalization_frequency = normalization_frequency,
            normalization_factor =
                calc_normalization_factor(poles, zeros, normalization_frequency,
                                            pz_transfer_function_type),
            zeros = zeros,
            poles = poles,
            name = 'Digitizer input voltage divider and antialiasing filter',
            input_units_description = 'Volts',
            output_units_description = 'Volts'))

        # Stage 2: ADC gain = 2
        self.stages.append(ResponseStage(
            len(self.stages)+1,
            stage_gain = 2.0,
            stage_gain_frequency = normalization_frequency,
            input_units = 'V',
            output_units = 'V',
            name = 'ADC PGA gain',
            input_units_description = 'Volts',
            output_units_description = 'Volts'))

        # Stage 3: ADC conversion: +/- VREF to +/- 2^23 counts.
        vref = 2.5
        self.stages.append(CoefficientsTypeResponseStage(
            len(self.stages)+1,
            stage_gain = 2**23 / vref,
            stage_gain_frequency = normalization_frequency,
            input_units = 'V',
            output_units = 'COUNTS',
            name = 'ADC sigma delta modulator',
            input_units_description = 'Volts',
            output_units_description = 'Digital counts',
            cf_transfer_function_type = 'DIGITAL',
            numerator = [1.0],
            denominator = [],
            # CS5532 - 256.0 KHz modulator frequency.
            decimation_input_sample_rate = 256e3,
            decimation_factor = 1,
            decimation_offset = 0,
            decimation_delay = 0,
            decimation_correction = 0))

        # Stage 4: ADC sinc5 digital filter.
        # ODR is 3200 Hz. Modulator decimation is 80, using a 5th order sinc filter.
        # Some of this is adapted from RESP.XX.ND129..HHZ.CS5532.ALL.2.LO.100
        self.stages.append(CoefficientsTypeResponseStage(
            len(self.stages)+1,
            stage_gain = 1.0,
            stage_gain_frequency = normalization_frequency,
            input_units = 'COUNTS',
            output_units = 'COUNTS',
            cf_transfer_function_type = 'DIGITAL',
            numerator = calc_sinc_filter_coefficients(order=5, length=31),  #FIXME
            denominator = [],
            decimation_input_sample_rate = 256e3,
            decimation_factor = 80,
            decimation_offset = 0,
            decimation_delay = 237 * 1.0/256e3,       # 237 modulator clocks: (N-1)/2
            decimation_correction = 237 * 1.0/256e3,
            name = 'ADC sinc5 digital filter',
            input_units_description = 'Digital counts',
            output_units_description = 'Digital counts'))

        # The data rate is futher decimated by a sinc3 filter with decimation ratio
        # of 32 to result in 100 Hz ODR.
        # Some of this is adapted from RESP.XX.ND129..HHZ.CS5532.ALL.2.LO.100
        self.stages.append(CoefficientsTypeResponseStage(
            len(self.stages)+1,
            stage_gain = 1.0,
            stage_gain_frequency = normalization_frequency,
            input_units = 'COUNTS',
            output_units = 'COUNTS',
            cf_transfer_function_type = 'DIGITAL',
            numerator = calc_sinc_filter_coefficients(order=3, length=32),
            denominator = [],
            decimation_input_sample_rate = 3200,
            decimation_factor = 32,
            decimation_offset = 0,
            decimation_delay = 62.0 / 3200,       # 62 clocks: (N-1)/2
            decimation_correction = 62.0 / 3200,
            name = 'ADC sinc3 digital filter',
            input_units_description = 'Digital counts',
            output_units_description = 'Digital counts'))

    def __str__(self):
        str = ''
        for s in self.stages:
            str += s.__str__() + '\n\n'
        return str

    def response(self):
        # Return an array of ResponseStages
        return self.stages


################################################################################
# Seiscape2 digitizer response.
# Based on the AD7175 ADC, in a single supported configuration:
# 4 channels at 125 Hz ODR per channel.
#
class Seiscape2Response:
    def __init__(self, divider_ratio=0.125, vref=2.5, odr=500, num_channels=4):
        self.odr = odr
        self.num_channels = num_channels
        self.stages = []

        # Stage 1: input voltage divider and antialiasing filter.
        poles = [complex('-586+0j')]           # 1/CR(parallel) = 93 Hz
        zeros = []
        pz_transfer_function_type = 'LAPLACE (RADIANS/SECOND)'
        normalization_frequency = 1.0
        self.stages.append(PolesZerosResponseStage(
            len(self.stages)+1,
            stage_gain = divider_ratio,
            stage_gain_frequency = normalization_frequency,
            input_units = 'V',
            output_units = 'V',
            pz_transfer_function_type = pz_transfer_function_type,
            normalization_frequency = normalization_frequency,
            normalization_factor =
                calc_normalization_factor(poles, zeros, normalization_frequency,
                                            pz_transfer_function_type),
            zeros = zeros,
            poles = poles,
            name = 'Digitizer input voltage divider and antialiasing filter',
            input_units_description = 'Volts',
            output_units_description = 'Volts'))

        # Stage 2: ADC conversion: +/- VREF to +/- 2^23 counts.
        # Modulator runs at MCLK/2.  MCLK is nominally 16 MHz.
        self.stages.append(CoefficientsTypeResponseStage(
            len(self.stages)+1,
            stage_gain = 2**23 / vref,
            stage_gain_frequency = normalization_frequency,
            input_units = 'V',
            output_units = 'COUNTS',
            name = 'ADC sigma delta modulator',
            input_units_description = 'Volts',
            output_units_description = 'Digital counts',
            cf_transfer_function_type = 'DIGITAL',
            numerator = [1.0],
            denominator = [],
            decimation_input_sample_rate = 8e6,
            decimation_factor = 1,
            decimation_offset = 0,
            decimation_delay = 0,
            decimation_correction = 0))

        # Stage 3: ADC sinc5 digital filter.
        # The assumption is that this is always decimate-by-32.
        # Webpage mentions that impulse response of sinc3 is 96 long, so a
        # sinc1 would be 12 coef long.
        # FIXME AD says: At a 250 kHz ODR, the AD7175 sinc5 + sinc1 is
        # configured directly as a sinc5 path with a −3 dB frequency of ~0.2 ×
        # ODR (50 kHz).
        # https://www.analog.com/en/resources/technical-articles/fundamental-principles-behind-sigma-delta-adc-topology-part2.html
        self.stages.append(CoefficientsTypeResponseStage(
            len(self.stages)+1,
            stage_gain = 1.0,
            stage_gain_frequency = normalization_frequency,
            input_units = 'COUNTS',
            output_units = 'COUNTS',
            cf_transfer_function_type = 'DIGITAL',
            numerator = calc_sinc_filter_coefficients(order=5, length=12),
            denominator = [],
            decimation_input_sample_rate = 8e6,
            decimation_factor = 32,
            decimation_offset = 0,      # FIXME
            decimation_delay = 0,       # FIXME
            decimation_correction = 0,  # FIXME
            name = 'ADC sinc5 digital filter',
            input_units_description = 'Digital counts',
            output_units_description = 'Digital counts'))

        ############################################################################
        # The data rate is futher decimated by a sinc1 with decimation ratio of 1
        # to 50000.
        # FIXME - Additionally there is channel sequencing. ADC set for 500 Hz
        # ODR with 4 channels in sequence.  So each channel has 125 Hz ODR.
        # FIXME - this is not right..

        # Stage 4: ADC sinc1 digital filter. Averager and decimator.
        self.stages.append(CoefficientsTypeResponseStage(
            len(self.stages)+1,
            stage_gain = 1.0,
            stage_gain_frequency = normalization_frequency,
            input_units = 'COUNTS',
            output_units = 'COUNTS',
            cf_transfer_function_type = 'DIGITAL',
            numerator = calc_sinc_filter_coefficients(order=1, length=2000),
            denominator = [],
            decimation_input_sample_rate = 250e3,
            decimation_factor = 2000,
            decimation_offset = 0,      # FIXME
            decimation_delay = 0,       # FIXME
            decimation_correction = 0,  # FIXME
            name = 'ADC sinc1 digital filter',
            input_units_description = 'Digital counts',
            output_units_description = 'Digital counts'))

    def __str__(self):
        str = ''
        for s in self.stages:
            str += s.__str__() + '\n\n'
        return str

    def response(self):
        # Return an array of ResponseStages
        return self.stages


################################################################################
# Calculate the normalization factor for a poles/zeros stage.
# Adapted from https://github.com/obspy/obspy/issues/2574
def calc_normalization_factor(poles, zeros, normalization_frequency, transfer_function_type):
    """
    Calculate the normalization factor for given poles-zeros

    The norm factor A0 is calculated such that
                       sequence_product_over_n(s - zero_n)
            A0 * abs(------------------------------------------) === 1
                       sequence_product_over_m(s - pole_m)
    for s_f=i*2pi*f if the transfer function is in radians
            i*f     if the transfer funtion is in Hertz
    """
    if not normalization_frequency:
        return None
    A0 = 1.0 + (1j * 0.0)
    if transfer_function_type == "LAPLACE (HERTZ)":
        s = 1j * normalization_frequency
    elif transfer_function_type == "LAPLACE (RADIANS/SECOND)":
        s = 1j * 2 * math.pi * normalization_frequency
    else:
        print("Don't know how to calculate normalization factor "
              "for z-transform poles and zeros!")
        return False
    for p in poles:
        A0 *= (s - p)
    for z in zeros:
        A0 /= (s - z)
    A0 = abs(A0)
    return A0

# Calculate FIR filter coefficients for an n-th order sinc filter.
def calc_sinc_filter_coefficients(order, length):

    # First order sinc is just a boxcar filter (moving average).
    coef = length * [1.0/length]

    # Convolve with itself multiple times for higher order sinc.
    for i in range(order-1):
        coef = convolve(coef, coef, mode='full', method='direct')

    print(order, 'order sinc filter length', len(coef))
    #print(coef)
    return coef

def combine_responses(sensor, digitizer):
    # Combine the sensor and digitizer responses.
    stages = []
    if sensor:
        stages.append(sensor)
    if digitizer:
        stages.extend(digitizer)
    # Fix up the sequence number for each stage.
    for i,s in enumerate(stages):
        s.stage_sequence_number = i+1
    return stages

def print_instrument_polynomial(poly):
    # Obspy InstrumentPolynomial doesn't have a __str__() method, so
    # implement it here.
    #ret = ("Instrument Polynomial:\n"
           #"\tFrequency lower bound: {frequency_lower_bound}\n"
           #"\tFrequency upper bound: {frequency_upper_bound}\n"
           #"\tInput units: {input_units}\n"
           #"\tInput units description: {input_units_description}\n"
           #"\tOutput units: {output_units}\n"
           #"\tOutput units description: {output_units_description}\n"
           #"\tCoefficients: {coefficients}\n")
    #ret = ret.format(**poly.__dict__)
    ret = ("Instrument Polynomial:\n"
           "\tFrequency lower bound: {}\n"
           "\tFrequency upper bound: {}\n"
           "\tInput units: {}\n"
           "\tInput units description: {}\n"
           "\tOutput units: {}\n"
           "\tOutput units description: {}\n"
           "\tCoefficients: {}\n")
    ret = ret.format(poly.frequency_lower_bound,
                poly.frequency_upper_bound,
                poly.input_units,
                poly.input_units_description,
                poly.output_units,
                poly.output_units_description,
                poly.coefficients)
    print(ret)

def print_verbose(response):
    if response.instrument_sensitivity:
        print(response.instrument_sensitivity)
    if response.instrument_polynomial:
        print_instrument_polynomial(response.instrument_polynomial)
    print(response, '\n')
    for s in response.response_stages:
        print(s, '\n')
    #print(response.get_sacpz())

#def generate_outputs(inv, net, sta, cha, response, filename=None, plot=False):
def generate_outputs(inv, net, sta, filename=None, plot=False):
    # Write it to a StationXML file.
    if not filename:
        filename = '{}_{}.xml'.format(net.code, sta.code)
    inv.write(filename, format="stationxml", validate=True)
    #inv.write(filename, format="stationxml", validate=False)

#    if plot:
#        # Plot the response of Yuma2 by itself, and the complete channel
#        # response.
#        response.plot(
#            min_freq=1e-3,
#            output='VEL',
#            start_stage=1,
#            end_stage=1,
#            plot_degrees=True,
#            unwrap_phase=True,
#            sampling_rate=2000,
#            label='Sensor response',
#            outfile="{}_{}_sensor.png".format(net.code, sta.code))
#
#        response.plot(
#            min_freq=1e-3,
#            output='VEL',
#            start_stage=2,
#            end_stage=len(response)-2,
#            plot_degrees=True,
#            unwrap_phase=True,
#            sampling_rate=2000,
#            label='Digitizer response',
#            outfile="{}_{}_digitizer.png".format(net.code, sta.code))
#
#        response.plot(
#            min_freq=1e-3,
#            output='VEL',
#            plot_degrees=True,
#            unwrap_phase=True,
#            sampling_rate=2000,
#            label='channel response',
#            outfile="{}_{}_channel.png".format(net.code, sta.code))

def create_channel(channel, location, latitude, longitude, elevation, depth,
    sensor_resp, digitizer_resp, sample_rate, input_units_str, input_units_desc,
    sensor=None, data_logger=None):

    # Velocity channels will use InstrumentSensitivity.
    # Temperature channels will use InstrumentPolynomial.
    instrument_sensitivity = None
    instrument_polynomial = None

    if sensor_resp and type(sensor_resp) == PolynomialResponseStage:
        # Need to calculate an overall InstrumentPolynomial instead of an
        # InstrumentSensitivity, based on all the stage gains.  Unfortunately,
        # obspy doesn't calculate this automatically.  Refer to the steps here:
        # https://docs.fdsn.org/projects/stationxml/en/latest/response.html?highlight=Temperature#ysi-44031-thermistor

        # First compute system gain of all the digitizer stages. (Assume velocity input near DC).
        sensitivity = InstrumentSensitivity(
            1.0,
            0.001,
            'M/S',
            'COUNTS',
            'Voltage',
            'Digital counts')

        digitizer_response = Response(
            instrument_sensitivity = sensitivity,
            response_stages = combine_responses(
                None,
                digitizer_resp))
        digitizer_response.recalculate_overall_sensitivity()
        system_gain = digitizer_response.instrument_sensitivity.value
        print(digitizer_response.instrument_sensitivity)

        # Then scale all of the sensor coefficients by the inverse nth power of the system gain.
        coef = sensor_resp.coefficients
        for i,c in enumerate(coef):
            coef[i] = c / (system_gain ** i)

        # Then create the InstrumentPolynomial using these scaled coefficients.
        instrument_polynomial = InstrumentPolynomial(
            input_units_str,
            'COUNTS',
            0, 1,
            0, 1,
            0, coef,
            input_units_description = input_units_desc,
            output_units_description = 'Digital counts')

        # Unfortunately, obspy will show an UNKNOWN for the channel response, but it will write the correct values to the stationXML file.

    else:
        # Set sensitivity to arbitrary values, as it will be recalculated from the
        # stage gains.
        instrument_sensitivity = InstrumentSensitivity(
            1.0,
            1.0,
            input_units_str, # 'M/S',
            'COUNTS',
            input_units_desc, # 'Velocity in meters per second',
            'Digital counts')

    # Combine the stages into a channel Response.
    response = Response(
        instrument_sensitivity = instrument_sensitivity,
        instrument_polynomial = instrument_polynomial,
        response_stages = combine_responses(
            sensor_resp,
            digitizer_resp))

    # This will fail for some input/output combinations such as Voltage, Temperature. Ignore.
    try:
        response.recalculate_overall_sensitivity()
    except Exception as e:
        print('Recalculate_overall_sensitivity failed:', e)
    print_verbose(response)

    cha = Channel(
        code = channel,
        location_code = location,
        latitude = latitude,
        longitude = longitude,
        elevation = elevation,
        depth = depth,
        azimuth = 0.0,
        dip = -90.0,
        sample_rate = sample_rate,
        sensor = sensor,
        data_logger = data_logger)
    cha.response = response
    return cha

def create_station_gblco():
    sta = Station(
        code = 'GBLCO',
        latitude = 43.50999,
        longitude = -120.24793,
        elevation = 1499.0,
        creation_date = obspy.UTCDateTime(2024, 6, 1),
        site = Site(
            name = 'GLASS BUTTES, LAKE COUNTY, OREGON',
            county = 'Lake',
            region = 'Oregon',
            country = 'USA'))

    # Vertical
    sta.channels.append(create_channel(
        channel = 'BHZ',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = Yuma2Response.lookup(serial_number='2').response(),
        digitizer_resp = Seiscape2Response().response(),
        sample_rate = 125.0,
        input_units_str = 'M/S',
        input_units_desc = 'Velocity in meters per second',
        sensor = Equipment(
            description='Velocity sensor',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 2'),
        data_logger = Equipment(
            description='',
            manufacturer='groundmotion.org',
            model='Seiscape2 rev A, Power Cape rev A, Beaglebone Green',
            serial_number='79cda1')))

    # Temperature sensor
    sta.channels.append(create_channel(
        channel = 'EVT',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = Yuma2Response.lookup(serial_number='2').temperature_response(),
        digitizer_resp = Seiscape2Response().response(),
        sample_rate = 125.0,
        input_units_str = 'degC',
        input_units_desc = 'Degrees Centigrade',
        sensor = Equipment(
            description='PCB temperature sensor',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 2'),
        data_logger = Equipment(
            description='',
            manufacturer='groundmotion.org',
            model='Seiscape2 rev A, Power Cape rev A, Beaglebone Green',
            serial_number='79cda1')))

    # Centering force
    sta.channels.append(create_channel(
        channel = 'EVC',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = None,
        digitizer_resp = Seiscape2Response().response(),
        sample_rate = 125.0,
        input_units_str = 'Volts',
        input_units_desc = 'Voltage',
        sensor = Equipment(
            description='Centering force',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 2'),
        data_logger = Equipment(
            description='',
            manufacturer='groundmotion.org',
            model='Seiscape2 rev A, Power Cape rev A, Beaglebone Green',
            serial_number='79cda1')))

    # Shorted inputs (for noise analysis)
    sta.channels.append(create_channel(
        channel = 'EVN',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = None,
        digitizer_resp = Seiscape2Response().response(),
        sample_rate = 125.0,
        input_units_str = 'Volts',
        input_units_desc = 'Voltage',
        sensor = Equipment(
            description='Shorted inputs at ADC mux, for noise analysis.'),
        data_logger = Equipment(
            manufacturer='groundmotion.org',
            model='Seiscape2 rev A, Power Cape rev A, Beaglebone Green',
            serial_number='79cda1')))
    return sta

def create_station_omdbo():
    sta = Station(
        code = 'OMDBO',
        latitude = 44.04410,
        longitude = -121.30930,
        elevation = 1118.0,
        creation_date = obspy.UTCDateTime(2021, 12, 26),
        site = Site(name = 'OLD MILL DISTRICT, BEND, OREGON'))

    cha = Channel(
        code = 'BHZ',
        location_code = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 0.0,
        azimuth = 0.0,
        dip = -90.0,
        sample_rate = 125)      # FIXME

    # Vertical
    sta.channels.append(create_channel(
        channel = 'BHZ',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = Yuma2Response.lookup(serial_number='1').response(),
        digitizer_resp = PsnAdc24Response().response(),
        sample_rate = 125.0,
        input_units_str = 'M/S',
        input_units_desc = 'Velocity in meters per second',
        sensor = Equipment(
            description='Velocity sensor',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 1'),
        data_logger = Equipment(
            description='',
            manufacturer='Webtronics',
            model='PSN-ADC24 v1.5',
            serial_number='')))

    # Temperature sensor
    # FIXME - instead, use PolynomialResponseStage to convert Temperature in degrees C to Voltage.
    sta.channels.append(create_channel(
        channel = 'LKS',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = Yuma2Response.lookup(serial_number='1').temperature_response(),
        digitizer_resp = PsnAdc24Response().response(),
        sample_rate = 1.0,
        input_units_str = 'degC',
        input_units_desc = 'Degrees Centigrade',
        sensor = Equipment(
            description='PCB temperature sensor',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 1'),
        data_logger = Equipment(
            description='',
            manufacturer='Webtronics',
            model='PSN-ADC24 v1.5',
            serial_number='')))

    # Centering force
    sta.channels.append(create_channel(
        channel = 'LEC',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = None,
        digitizer_resp = PsnAdc24Response().response(),
        sample_rate = 1.0,
        input_units_str = 'Volts',
        input_units_desc = 'Voltage',
        sensor = Equipment(
            description='Centering force',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 1'),
        data_logger = Equipment(
            description='',
            manufacturer='Webtronics',
            model='PSN-ADC24 v1.5',
            serial_number='')))
    return sta

def create_station_xxxxx():
    yuma_sn = '3'
    sta = Station(
        code = 'XXXXX',
        latitude = 44.04410,
        longitude = -121.30930,
        elevation = 1118.0,
        creation_date = obspy.UTCDateTime(2024, 8, 3),
        site = Site(name = 'TESTING ONLY. DO NOT USE.'))

    # Vertical
    sta.channels.append(create_channel(
        channel = 'BHZ',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = Yuma2Response.lookup(serial_number=yuma_sn).response(),
        digitizer_resp = Seiscape2Response().response(),
        sample_rate = 125.0,
        input_units_str = 'M/S',
        input_units_desc = 'Velocity in meters per second',
        sensor = Equipment(
            description='Velocity sensor',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 2'),
        data_logger = Equipment(
            description='',
            manufacturer='groundmotion.org',
            model='Seiscape2 rev A, Power Cape rev A, Beaglebone Green',
            serial_number='79cda1')))

    # Temperature sensor
    sta.channels.append(create_channel(
        channel = 'EVT',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = Yuma2Response.lookup(serial_number=yuma_sn).temperature_response(),
        digitizer_resp = Seiscape2Response().response(),
        sample_rate = 125.0,
        input_units_str = 'degC',
        input_units_desc = 'Degrees Centigrade',
        sensor = Equipment(
            description='PCB temperature sensor',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 2'),
        data_logger = Equipment(
            description='',
            manufacturer='groundmotion.org',
            model='Seiscape2 rev A, Power Cape rev A, Beaglebone Green',
            serial_number='79cda1')))

    # Centering force
    sta.channels.append(create_channel(
        channel = 'EVC',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = None,
        digitizer_resp = Seiscape2Response().response(),
        sample_rate = 125.0,
        input_units_str = 'Volts',
        input_units_desc = 'Voltage',
        sensor = Equipment(
            description='Centering force',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 2'),
        data_logger = Equipment(
            description='',
            manufacturer='groundmotion.org',
            model='Seiscape2 rev A, Power Cape rev A, Beaglebone Green',
            serial_number='79cda1')))

    # Shorted inputs (for noise analysis)
    sta.channels.append(create_channel(
        channel = 'EVN',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = None,
        digitizer_resp = Seiscape2Response().response(),
        sample_rate = 125.0,
        input_units_str = 'Volts',
        input_units_desc = 'Voltage',
        sensor = Equipment(
            description='Shorted inputs at ADC mux, for noise analysis.'),
        data_logger = Equipment(
            manufacturer='groundmotion.org',
            model='Seiscape2 rev A, Power Cape rev A, Beaglebone Green',
            serial_number='79cda1')))
    return sta

def create_response_files():
    def create_inv_net():
        inv = Inventory(
            networks = [],
            source = 'groundmotion.org')
        net = Network(
            code = 'AM',
            stations = [],
            description = 'Citizen scientist earthquake monitoring network.')
        return inv, net

    # Station GBLCO
    gblco = create_station_gblco()
    inv, net = create_inv_net()
    net.stations.append(gblco)
    inv.networks.append(net)
    print(inv)
    generate_outputs(inv, net, gblco)

    # Station OMDBO
    omdbo = create_station_omdbo()
    inv, net = create_inv_net()
    net.stations.append(omdbo)
    inv.networks.append(net)
    print(inv)
    generate_outputs(inv, net, omdbo)

    # Station XXXXX
    xxxxx = create_station_xxxxx()
    inv, net = create_inv_net()
    net.stations.append(xxxxx)
    inv.networks.append(net)
    print(inv)
    generate_outputs(inv, net, xxxxx)

    # Generate one combined file containing both stations.
    net.stations.append(omdbo)
    net.stations.append(gblco)
    print(inv)
    generate_outputs(inv, net, None, filename='all_stations.xml')

    # TODO - Also plot the response for Yuma2 and entire path.


if __name__ == '__main__':
    create_response_files()
