#!/usr/bin/python3
# Create a StationXML file describing the Yuma seismometer and digitizer
#
# Refer to:
# https://docs.fdsn.org/projects/stationxml/en/latest/response.html#broadband-sensor
# https://docs.obspy.org/tutorial/code_snippets/stationxml_file_from_scratch.html
# https://docs.obspy.org/packages/obspy.clients.nrl.html

import obspy
import cmath
import math
from obspy.core.inventory import Inventory, Network, Station, Channel, Site
from obspy.core.inventory import InstrumentSensitivity, Response, ResponseStage
from obspy.core.inventory import PolesZerosResponseStage, CoefficientsTypeResponseStage
from obspy.clients.nrl import NRL
from scipy.signal import convolve

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
# FIXME AD says: At a 250 kHz ODR, the AD7175 sinc5 + sinc1 is configured directly as a sinc5 path with a −3 dB frequency of ~0.2 × ODR (50 kHz).
# https://www.analog.com/en/resources/technical-articles/fundamental-principles-behind-sigma-delta-adc-topology-part2.html
def calc_sinc_filter_coefficients(order, length):

    # First order sinc is just a boxcar filter (moving average).
    coef = length * [1.0/length]
    
    # Convolve with itself multiple times for higher order sinc.
    for i in range(order-1):
        coef = convolve(coef, coef, mode='full', method='direct')

    #print(order, 'order sinc filter length', len(coef))
    #print(coef)
    return coef


# Define the channel response as a series of stages.
stages = []

################################################################################
# Stage 1: Yuma seismometer: m/sec to volts. 
# Define the instrument sensitivity as a scalar: meters/sec to volts.
# This is for unit #2, calculated in Loop8Y.xls.
generator_constant = 844.49   # volt-sec / meter

pz_transfer_function_type = 'LAPLACE (RADIANS/SECOND)'
poles = [
    # FIXME - the double pole location may be incorrect - response plot shows
    # huge gain peaking.  Is it possible that Loop8Y.xls might have swapped the
    # real and imaginary parts of the double pole??
    #complex('-8.641e-4+0.08584j'),
    #complex('-8.641e-4-0.08584j'),
    complex('-0.085842+8.651e-4j'),
    complex('-0.085842-8.651e-4j'),
    complex('-209.7+0j'),
    complex('-1000+0j'),
    complex('-1002632+0j') ]
zeros = [
    complex('0+0j'),
    complex('-4.181e-6+0j') ]
normalization_frequency = 1.0

stages.append(PolesZerosResponseStage(
    len(stages)+1,
    stage_gain = generator_constant, 
    stage_gain_frequency = normalization_frequency,
    input_units = 'M/S', 
    output_units = 'V', 
    pz_transfer_function_type = pz_transfer_function_type,
    normalization_frequency = normalization_frequency,
    normalization_factor = 
        calc_normalization_factor(poles, zeros, normalization_frequency,
                                    pz_transfer_function_type),
    zeros = zeros,
    poles = poles,
    # Note: in StationXML file only the name of stage[0] is used.
    name = 'Yuma2 mechanical rev 4.3, electrical rev 4.0',
    input_units_description = 'Velocity in meters per second', 
    output_units_description = 'Volts'))
    
################################################################################
# Stage 2: Digitizer input voltage divider and antialiasing filter. gain < 1.
pz_transfer_function_type = 'LAPLACE (RADIANS/SECOND)'
poles = [complex('-586+0j')]           # 1/CR(parallel) = 93 Hz
zeros = []
normalization_frequency = 1.0
stages.append(PolesZerosResponseStage(
    len(stages)+1,
    stage_gain = 1.0/8,                     # divide by 8
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

################################################################################
# Stage 3: ADC gain = 1
stages.append(ResponseStage(
    len(stages)+1,
    stage_gain = 1.0,
    stage_gain_frequency = normalization_frequency,
    input_units = 'V', 
    output_units = 'V', 
    name = 'ADC PGA gain',
    input_units_description = 'Volts', 
    output_units_description = 'Volts'))
    
################################################################################
# Stage 4: ADC conversion: +/- VREF to +/- 2^23 counts.
vref = 2.5
stages.append(CoefficientsTypeResponseStage(
    len(stages)+1,
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
    # AD7175 - 8 MHz modulator frequency.
    decimation_input_sample_rate = 8e6,
    decimation_factor = 1,
    decimation_offset = 0,
    decimation_delay = 0,
    decimation_correction = 0))

################################################################################
## Stage 5: ADC sinc5 digital filter.
# ODR is 5 Hz to 250 KHz. So modulator decimation is min 32, using a 5th order sinc.
# Webpage mentions that impulse response of sinc3 is 96 long, so a sinc1 would be 12 coef long.
stages.append(CoefficientsTypeResponseStage(
    len(stages)+1, 
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

################################################################################
# The data rate is futher decimated by a sinc1 with decimation ratio of 1 to 50000.
# Additionally there is channel sequencing. ADC set for 500 Hz ODR with 4 channels in sequence.
# So each channel has 125 Hz ODR.
# FIXME - this is not right..

# Stage 6: ADC sinc1 digital filter. Averager and decimator.
stages.append(CoefficientsTypeResponseStage(
    len(stages)+1, 
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

################################################################################
# Set sensitivity to arbitrary values, as it will be recalculated from the
# stage gains.
instrument_sensitivity = InstrumentSensitivity(
    1.0, # generator_constant, 
    1.0, # frequency, 
    'M/S', 
    'COUNTS', 
    'Velocity in meters per second', 
    'Digital counts')

# Combine the stages into a channel Response.
response = Response(
    instrument_sensitivity = instrument_sensitivity, 
    response_stages = stages)
response.recalculate_overall_sensitivity()

# By default this accesses the NRL online. Offline copies of the NRL can
# also be used instead
#nrl = NRL()
# The contents of the NRL can be explored interactively in a Python prompt,
# see API documentation of NRL submodule:
# http://docs.obspy.org/packages/obspy.clients.nrl.html
# Here we assume that the end point of data logger and sensor are already
# known:
#response = nrl.get_response( # doctest: +SKIP
#    sensor_keys=['Streckeisen', 'STS-1', '360 seconds'],
#    datalogger_keys=['REF TEK', 'RT 130 & 130-SMA', '1', '200'])
#
# From STS-1 and REF TEK:
# Channel Response
#	From M/S (Velocity in Meters per Second) to COUNTS (Digital Counts)
#	Overall Sensitivity: 1.50991e+09 defined at 0.020 Hz
#	10 stages:
#		Stage 1: PolesZerosResponseStage from M/S to V, gain: 2400
#		Stage 2: ResponseStage from V to V, gain: 1
#		Stage 3: CoefficientsTypeResponseStage from V to COUNTS, gain: 629129
#		Stage 4: CoefficientsTypeResponseStage from COUNTS to COUNTS, gain: 1
#		Stage 5: CoefficientsTypeResponseStage from COUNTS to COUNTS, gain: 1
#		Stage 6: CoefficientsTypeResponseStage from COUNTS to COUNTS, gain: 1
#		Stage 7: CoefficientsTypeResponseStage from COUNTS to COUNTS, gain: 1
#		Stage 8: CoefficientsTypeResponseStage from COUNTS to COUNTS, gain: 1
#		Stage 9: CoefficientsTypeResponseStage from COUNTS to COUNTS, gain: 1
#		Stage 10: CoefficientsTypeResponseStage from COUNTS to COUNTS, gain: 1
# Instrument Sensitivity:
#	Value: 1509906780.0735059
#	Frequency: 0.02
#	Input units: M/S
#	Input units description: Velocity in Meters per Second
#	Output units: COUNTS
#	Output units description: Digital Counts

def print_verbose(response):
    print(response.instrument_sensitivity)
    print(response, '\n')
    for s in response.response_stages:
        print(s, '\n')
    print(response.get_sacpz())

def generate_outputs(inv, net, sta, chan, response):
    cha.response = response
    sta.channels.append(cha)
    net.stations.append(sta)
    inv.networks.append(net)

    # Write it to a StationXML file. We also force a validation against
    # the StationXML schema to ensure it produces a valid StationXML file.
    #
    # Note that it is also possible to serialize to any of the other inventory
    # output formats ObsPy supports.
    filename = '{}_{}.xml'.format(net.code, sta.code)
    inv.write(filename, format="stationxml", validate=True)

    #filename = '{}_{}.sacpz'.format(net.code, sta.code)
    #inv.write(filename, format="SACPZ")
    #inv.write("station.kml", format="KML")
    print(inv)

    # Plot the response of Yuma2 by itself, and the complete channel response.
    response.plot(
        min_freq=1e-3, 
        output='VEL', 
        start_stage=1, 
        end_stage=1, 
        plot_degrees=True, 
        unwrap_phase=True, 
        sampling_rate=2000, 
        label='Yuma2 response', 
        outfile="response_yuma.png")

    response.plot(
        min_freq=1e-3, 
        output='VEL', 
        plot_degrees=True, 
        unwrap_phase=True, 
        sampling_rate=2000, 
        label='channel response', 
        outfile="response_channel.png")

# Create all the various objects. These strongly follow the hierarchy of
# StationXML files.
inv = Inventory(
    networks = [],
    source = 'groundmotion.org')

net = Network(
    code = 'AM',
    stations = [],
    description = 'Citizen scientist earthquake monitoring network.')

sta = Station(
    code = 'GBLCO',
    latitude = 43.50999,
    longitude = -120.24793,
    elevation = 1499.0,
    creation_date = obspy.UTCDateTime(2024, 6, 1),
    site = Site(name = 'GLASS BUTTES, LAKE COUNTY, OREGON'))

cha = Channel(
    code = 'BHZ',
    location_code = '01',
    latitude = sta.latitude,
    longitude = sta.longitude,
    elevation = sta.elevation,
    depth = 1.0,
    azimuth = 0.0,
    dip = -90.0,
    sample_rate = 125)

# Create the StationXML file.
generate_outputs(inv, net, sta, cha, response)
print_verbose(response)

