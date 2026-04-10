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
from obspy.core.inventory.util import Equipment, Operator, Person
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
        #"sensitivity": 1237,                    # volt-sec/meter
        "sensitivity": 842,                     # volt-sec/meter
        "poles": [                              # rads/sec
            complex('-0.08361+8.235e-04j'),
            complex('-0.08361-8.235e-04j'),
            complex('-1000+0j'),
            complex('-2135+0j'),
            complex('-1002632+0j') ],
        "zeros": [
            complex('0+0j'),
            complex('-4.105e-06+0j') ]
    }
    config["2"] = {                             # serial number 2
        "sensitivity": 844.5,
        "poles": [
            complex('-0.085842+8.651e-4j'),
            complex('-0.085842-8.651e-4j'),
            complex('-1000+0j'),
            complex('-2135+0j'),
            complex('-1002632+0j') ],
        "zeros": [
            complex('0+0j'),
            complex('-4.181e-6+0j') ]
    }
    config["3"] = {                             # serial number 3
        "sensitivity": 1083,
        "poles": [
            complex('-0.08375+8.264e-4j'),
            complex('-0.08375-8.264e-4j'),
            complex('-1005+0j'),
            complex('-2135+0j'),
            complex('-1000100+0j') ],
        "zeros": [
            complex('0+0j'),
            complex('-4.114e-6+0j') ],
    }
    config["4"] = {                             # serial number 4 (estimated)
        "sensitivity": 1266,                    # estimate
        "poles": [
            complex('-0.08375+8.264e-4j'),
            complex('-0.08375-8.264e-4j'),
            complex('-1005+0j'),
            complex('-2135+0j'),
            complex('-1000100+0j') ],
        "zeros": [
            complex('0+0j'),
            complex('-4.114e-6+0j') ],
    }

    # Usually not instantiated directly.  Use the lookup() method instead.
    def __init__(self, serial_number, sensitivity, poles, zeros):
        self.serial_number = serial_number
        self.normalization_frequency = 1.0
        self.pz_transfer_function_type = 'LAPLACE (RADIANS/SECOND)'
        self.response_stage = PolesZerosResponseStage(
            1,
            stage_gain = sensitivity,
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
        return cls(serial_number, data['sensitivity'], data['poles'], data['zeros'])


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

        # Stage 2: ADC internal PGA (programmable gain amplifier), gain = 2.
        # Represented as a poles/zeros stage with no poles and no zeros
        # (flat frequency response) so that the name is preserved in the
        # StationXML output.  All information is in the stage gain.
        self.stages.append(PolesZerosResponseStage(
            len(self.stages)+1,
            stage_gain = 2.0,
            stage_gain_frequency = normalization_frequency,
            input_units = 'V',
            output_units = 'V',
            pz_transfer_function_type = 'LAPLACE (RADIANS/SECOND)',
            normalization_frequency = normalization_frequency,
            normalization_factor = 1.0,
            zeros = [],
            poles = [],
            name = 'ADC internal PGA (gain only, gain=2)',
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
        # Group delay per CS5532 datasheet: 237 modulator clocks = (N*R-1)/2 - 3 = (5*80-1)/2 - 3.
        self.stages.append(CoefficientsTypeResponseStage(
            len(self.stages)+1,
            stage_gain = 1.0,
            stage_gain_frequency = normalization_frequency,
            input_units = 'COUNTS',
            output_units = 'COUNTS',
            cf_transfer_function_type = 'DIGITAL',
            numerator = calc_sinc_filter_coefficients(order=5, decimation_factor=80),
            denominator = [],
            decimation_input_sample_rate = 256e3,
            decimation_factor = 80,
            decimation_offset = 0,
            decimation_delay = 237 * 1.0/256e3,       # 237 modulator clocks (from CS5532 datasheet)
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
            numerator = calc_sinc_filter_coefficients(order=3, decimation_factor=32),
            denominator = [],
            decimation_input_sample_rate = 3200,
            decimation_factor = 32,
            decimation_offset = 0,
            decimation_delay = 62.0 / 3200,       # 62 clocks (from CS5532 datasheet)
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
        # AD7175 sinc5+sinc1 filter path. The sinc5 always uses decimation ratio=32,
        # giving an intermediate rate of 8 MHz / 32 = 250 kHz.
        # Group delay = (N*R - 1) / (2 * f_in) = (5*32 - 1) / (2 * 8e6) ≈ 9.94 µs.
        # Ref: https://www.analog.com/en/resources/technical-articles/fundamental-principles-behind-sigma-delta-adc-topology-part2.html
        sinc5_R = 32
        sinc5_delay = (5 * sinc5_R - 1) / (2 * 8e6)
        self.stages.append(CoefficientsTypeResponseStage(
            len(self.stages)+1,
            stage_gain = 1.0,
            stage_gain_frequency = normalization_frequency,
            input_units = 'COUNTS',
            output_units = 'COUNTS',
            cf_transfer_function_type = 'DIGITAL',
            numerator = calc_sinc_filter_coefficients(order=5, decimation_factor=sinc5_R),
            denominator = [],
            decimation_input_sample_rate = 8e6,
            decimation_factor = sinc5_R,
            decimation_offset = 0,
            decimation_delay = sinc5_delay,
            decimation_correction = sinc5_delay,
            name = 'ADC sinc5 digital filter',
            input_units_description = 'Digital counts',
            output_units_description = 'Digital counts'))

        # Stage 4: Decimate-by-R averaging filter.
        # ADC is configured for 500 Hz ODR with 4 channels in sequence, so each
        # channel receives output at 125 Hz. From the sinc5 output (250 kHz),
        # the effective decimation per channel is 250000 / 125 = 2000.
        # Represented with a single unity coefficient (numerator=[1.0]) rather
        # than listing all R identical taps — the decimation factor fully defines
        # the filter; numerator=[1.0] satisfies evalresp's requirement for a
        # filter type on any stage that carries a decimation block.
        # Group delay = (R - 1) / (2 * f_in) = (2000 - 1) / (2 * 250e3) ≈ 3.998 ms.
        sinc1_R = int(250e3 / (odr / num_channels))
        sinc1_delay = (sinc1_R - 1) / (2 * 250e3)
        self.stages.append(CoefficientsTypeResponseStage(
            len(self.stages)+1,
            stage_gain = 1.0,
            stage_gain_frequency = normalization_frequency,
            input_units = 'COUNTS',
            output_units = 'COUNTS',
            cf_transfer_function_type = 'DIGITAL',
            numerator = [1.0],
            denominator = [],
            name = 'ADC decimate-by-%d averaging filter' % sinc1_R,
            input_units_description = 'Digital counts',
            output_units_description = 'Digital counts',
            decimation_input_sample_rate = 250e3,
            decimation_factor = sinc1_R,
            decimation_offset = 0,
            decimation_delay = sinc1_delay,
            decimation_correction = sinc1_delay))

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

# Calculate FIR filter coefficients for an n-th order sinc (CIC) filter.
# decimation_factor is the decimation ratio R of the filter stage.
# The resulting filter has N*(R-1)+1 coefficients.
def calc_sinc_filter_coefficients(order, decimation_factor):

    # First order sinc is a boxcar (moving average) of length R.
    box = decimation_factor * [1.0/decimation_factor]

    # Convolve with the original box filter (N-1) times to get sincN.
    # Note: must convolve with the original box each time, not with itself,
    # to avoid doubling the effective order on each iteration.
    coef = box.copy()
    for i in range(order-1):
        coef = convolve(coef, box, mode='full', method='direct')

    coef = list(coef)
    print(order, 'order sinc filter, R=%d, length=%d' % (decimation_factor, len(coef)))
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
    # validate=False: ObsPy 1.5+ misplaces InstrumentPolynomial (temperature
    # channels) when serializing, causing spurious schema validation failures.
    inv.write(filename, format="stationxml", validate=False)

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
    sensor=None, data_logger=None, start_date=None):

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
        data_logger = data_logger,
        start_date = start_date)
    cha.response = response
    return cha

def create_station_gblco():
    start = obspy.UTCDateTime(2024, 6, 1)
    sta = Station(
        code = 'GBLCO',
        latitude = 43.50999,
        longitude = -120.24793,
        elevation = 1499.0,
        creation_date = start,
        start_date = start,
        site = Site(
            name = 'GLASS BUTTES, LAKE COUNTY, OREGON',
            county = 'Lake',
            region = 'Oregon',
            country = 'USA'))

    # Vertical seismometer (BHZ: using B-band to match existing MiniSEED data;
    # TODO: rename to HHZ (H-band = 80-250 sps) once data files are updated)
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
        start_date = start,
        sensor = Equipment(
            description='Velocity sensor',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 2'),
        data_logger = Equipment(
            description='Digitizer',
            manufacturer='groundmotion.org',
            model='Seiscape2 rev A, Power Cape rev A, Beaglebone Green',
            serial_number='79cda1')))

    # Temperature sensor (EKS: E-band = 80-250 sps, K = temperature, S = scalar)
    sta.channels.append(create_channel(
        channel = 'EKS',
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
        start_date = start,
        sensor = Equipment(
            description='PCB temperature sensor',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 2'),
        data_logger = Equipment(
            description='Digitizer',
            manufacturer='groundmotion.org',
            model='Seiscape2 rev A, Power Cape rev A, Beaglebone Green',
            serial_number='79cda1')))

    # Centering force / mass position (EMZ: E-band, M = mass position, Z = vertical)
    sta.channels.append(create_channel(
        channel = 'EMZ',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = None,
        digitizer_resp = Seiscape2Response().response(),
        sample_rate = 125.0,
        input_units_str = 'V',
        input_units_desc = 'Volts',
        start_date = start,
        sensor = Equipment(
            description='Centering force (mass position monitor)',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 2'),
        data_logger = Equipment(
            description='Digitizer',
            manufacturer='groundmotion.org',
            model='Seiscape2 rev A, Power Cape rev A, Beaglebone Green',
            serial_number='79cda1')))

    # Shorted inputs (EXZ: E-band, X = experimental/non-standard, Z = vertical)
    sta.channels.append(create_channel(
        channel = 'EXZ',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = None,
        digitizer_resp = Seiscape2Response().response(),
        sample_rate = 125.0,
        input_units_str = 'V',
        input_units_desc = 'Volts',
        start_date = start,
        sensor = Equipment(
            description='Shorted inputs at ADC mux, for noise analysis.'),
        data_logger = Equipment(
            description='Digitizer',
            manufacturer='groundmotion.org',
            model='Seiscape2 rev A, Power Cape rev A, Beaglebone Green',
            serial_number='79cda1')))
    return sta

def create_station_omdbo():
    start = obspy.UTCDateTime(2021, 12, 26)
    sta = Station(
        code = 'OMDBO',
        latitude = 44.04410,
        longitude = -121.30930,
        elevation = 1118.0,
        creation_date = start,
        start_date = start,
        site = Site(name = 'OLD MILL DISTRICT, BEND, OREGON'))

    # Vertical seismometer (BHZ: using B-band to match existing MiniSEED data;
    # TODO: rename to HHZ (H-band = 80-250 sps) once data files are updated)
    sta.channels.append(create_channel(
        channel = 'BHZ',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = Yuma2Response.lookup(serial_number='4').response(),
        digitizer_resp = PsnAdc24Response().response(),
        sample_rate = 125.0,
        input_units_str = 'M/S',
        input_units_desc = 'Velocity in meters per second',
        start_date = start,
        sensor = Equipment(
            description='Velocity sensor',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 4'),
        data_logger = Equipment(
            description='Digitizer',
            manufacturer='Webtronics',
            model='PSN-ADC24 v1.5',
            serial_number='')))

    # Temperature sensor (LKS: L-band = 1 sps, K = temperature, S = scalar)
    sta.channels.append(create_channel(
        channel = 'LKS',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = Yuma2Response.lookup(serial_number='4').temperature_response(),
        digitizer_resp = PsnAdc24Response().response(),
        sample_rate = 1.0,
        input_units_str = 'degC',
        input_units_desc = 'Degrees Centigrade',
        start_date = start,
        sensor = Equipment(
            description='PCB temperature sensor',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 4'),
        data_logger = Equipment(
            description='Digitizer',
            manufacturer='Webtronics',
            model='PSN-ADC24 v1.5',
            serial_number='')))

    # Centering force / mass position (LMZ: L-band = 1 sps, M = mass position, Z = vertical)
    sta.channels.append(create_channel(
        channel = 'LMZ',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = None,
        digitizer_resp = PsnAdc24Response().response(),
        sample_rate = 1.0,
        input_units_str = 'V',
        input_units_desc = 'Volts',
        start_date = start,
        sensor = Equipment(
            description='Centering force (mass position monitor)',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 4'),
        data_logger = Equipment(
            description='Digitizer',
            manufacturer='Webtronics',
            model='PSN-ADC24 v1.5',
            serial_number='')))
    return sta

def create_station_bccwa():
    start = obspy.UTCDateTime(2025, 5, 14)
    sta = Station(
        code = 'BCCWA',
        latitude = 45.617450,
        longitude = -122.498994,
        elevation = 88.0,
        creation_date = start,
        start_date = start,
        site = Site(name = 'BENNINGTON, CLARK COUNTY, WASHINGTON'))

    # Vertical seismometer (BHZ: using B-band to match existing MiniSEED data;
    # TODO: rename to HHZ (H-band = 80-250 sps) once data files are updated)
    sta.channels.append(create_channel(
        channel = 'BHZ',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = Yuma2Response.lookup(serial_number='4').response(),
        digitizer_resp = PsnAdc24Response().response(),
        sample_rate = 100.0,
        input_units_str = 'M/S',
        input_units_desc = 'Velocity in meters per second',
        start_date = start,
        sensor = Equipment(
            description='Velocity sensor',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 4'),
        data_logger = Equipment(
            description='Digitizer',
            manufacturer='Webtronics',
            model='PSN-ADC24 v1.5',
            serial_number='')))

    # LKS and LMZ have a software decimation-by-100 averaging filter on the
    # digitizer after the ADC chain (100 Hz -> 100/100 = 1.0 Hz).
    averager_R = 100
    averager_input_rate = 100.0
    averager_output_rate = averager_input_rate / averager_R   # 0.78125 Hz
    averager_delay = (averager_R - 1) / (2 * averager_input_rate)  # 0.635 s
    averager_stage = CoefficientsTypeResponseStage(
        0,   # renumbered by combine_responses
        stage_gain = 1.0,
        stage_gain_frequency = 1.0,
        input_units = 'COUNTS',
        output_units = 'COUNTS',
        cf_transfer_function_type = 'DIGITAL',
        numerator = [1.0],
        denominator = [],
        name = 'Software decimate-by-%d averaging filter' % averager_R,
        input_units_description = 'Digital counts',
        output_units_description = 'Digital counts',
        decimation_input_sample_rate = averager_input_rate,
        decimation_factor = averager_R,
        decimation_offset = 0,
        decimation_delay = averager_delay,
        decimation_correction = averager_delay)
    adc_plus_averager = PsnAdc24Response().response() + [averager_stage]

    # Temperature sensor (LKS)
    sta.channels.append(create_channel(
        channel = 'LKS',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = Yuma2Response.lookup(serial_number='4').temperature_response(),
        digitizer_resp = adc_plus_averager,
        sample_rate = averager_output_rate,
        input_units_str = 'degC',
        input_units_desc = 'Degrees Centigrade',
        start_date = start,
        sensor = Equipment(
            description='PCB temperature sensor',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 4'),
        data_logger = Equipment(
            description='Digitizer',
            manufacturer='Webtronics',
            model='PSN-ADC24 v1.5',
            serial_number='')))

    # Centering force / mass position (LMZ)
    sta.channels.append(create_channel(
        channel = 'LMZ',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = None,
        digitizer_resp = adc_plus_averager,
        sample_rate = averager_output_rate,
        input_units_str = 'V',
        input_units_desc = 'Volts',
        start_date = start,
        sensor = Equipment(
            description='Centering force (mass position monitor)',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 4'),
        data_logger = Equipment(
            description='Digitizer',
            manufacturer='Webtronics',
            model='PSN-ADC24 v1.5',
            serial_number='')))
    return sta

def create_station_xxxxx():
    yuma_sn = '3'
    start = obspy.UTCDateTime(2024, 8, 3)
    sta = Station(
        code = 'XXXXX',
        latitude = 44.04410,
        longitude = -121.30930,
        elevation = 1118.0,
        creation_date = start,
        start_date = start,
        site = Site(name = 'TESTING ONLY. DO NOT USE.'))

    # Vertical (BHZ: TODO rename to HHZ once data files are updated)
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
        start_date = start,
        sensor = Equipment(
            description='Velocity sensor',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 2'),
        data_logger = Equipment(
            description='Digitizer',
            manufacturer='groundmotion.org',
            model='Seiscape2 rev A, Power Cape rev A, Beaglebone Green',
            serial_number='79cda1')))

    # Temperature sensor
    sta.channels.append(create_channel(
        channel = 'EKS',
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
        start_date = start,
        sensor = Equipment(
            description='PCB temperature sensor',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 2'),
        data_logger = Equipment(
            description='Digitizer',
            manufacturer='groundmotion.org',
            model='Seiscape2 rev A, Power Cape rev A, Beaglebone Green',
            serial_number='79cda1')))

    # Centering force / mass position
    sta.channels.append(create_channel(
        channel = 'EMZ',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = None,
        digitizer_resp = Seiscape2Response().response(),
        sample_rate = 125.0,
        input_units_str = 'V',
        input_units_desc = 'Volts',
        start_date = start,
        sensor = Equipment(
            description='Centering force (mass position monitor)',
            manufacturer='Nelson / Nordgren',
            model='Yuma2 FBV mechanical rev 4.3, electrical rev 4.0',
            serial_number='BK 2'),
        data_logger = Equipment(
            description='Digitizer',
            manufacturer='groundmotion.org',
            model='Seiscape2 rev A, Power Cape rev A, Beaglebone Green',
            serial_number='79cda1')))

    # Shorted inputs (for noise analysis)
    sta.channels.append(create_channel(
        channel = 'EXZ',
        location = '01',
        latitude = sta.latitude,
        longitude = sta.longitude,
        elevation = sta.elevation,
        depth = 1.0,
        sensor_resp = None,
        digitizer_resp = Seiscape2Response().response(),
        sample_rate = 125.0,
        input_units_str = 'V',
        input_units_desc = 'Volts',
        start_date = start,
        sensor = Equipment(
            description='Shorted inputs at ADC mux, for noise analysis.'),
        data_logger = Equipment(
            description='Digitizer',
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
            description = 'Citizen scientist earthquake monitoring network.',
            start_date = obspy.UTCDateTime(2021, 12, 26),
            operators = [Operator(
                agency = 'groundmotion.org',
                contacts = [Person(emails = ['brian@groundmotion.org'])])])
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

    # Station BCCWA
    bccwa = create_station_bccwa()
    inv, net = create_inv_net()
    net.stations.append(bccwa)
    inv.networks.append(net)
    print(inv)
    generate_outputs(inv, net, bccwa)

    # Station XXXXX
    xxxxx = create_station_xxxxx()
    inv, net = create_inv_net()
    net.stations.append(xxxxx)
    inv.networks.append(net)
    print(inv)
    generate_outputs(inv, net, xxxxx)

    # Generate one combined file containing all stations.
    net.stations.append(omdbo)
    net.stations.append(bccwa)
    net.stations.append(gblco)
    print(inv)
    generate_outputs(inv, net, None, filename='all_stations.xml')

    # TODO - Also plot the response for Yuma2 and entire path.


if __name__ == '__main__':
    create_response_files()
