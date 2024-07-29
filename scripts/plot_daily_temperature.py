# Read data from Seedlink server and generate daily temperature plot.

from matplotlib.dates import HourLocator
from obspy.clients.seedlink.basic_client import Client as SeedlinkClient
from obspy.clients.seedlink.easyseedlink import create_client
from obspy.clients.fdsn import Client as FdsnClient
from obspy.geodetics.base import gps2dist_azimuth
from obspy.core.event import Catalog
from obspy.core.stream import Stream
from obspy.taup.tau import TauPyModel
from obspy import UTCDateTime
from obspy import read, read_inventory
import matplotlib.pyplot as plt
import numpy as np
import gc

################################################################################

# Read the station data from a local file.
def GetLocalData(net, station, loc, chan, year=0, doy=0):
    try:
        #st = read('%s.%s.%s.%s.mseed' % (net, station, loc, chan))
        st = read('/data/seismometer_data/mseed/%s.%s.%s.%s.%d.%d.mseed' % (net, station, loc, chan, year, doy))
        return st
    except:
        return None

def GetLocalDataRange(net, station, loc, chan, starttime, endtime):
    year = starttime._get_year()
    doy = starttime._get_julday()
    end_year = starttime._get_year()
    end_doy = endtime._get_julday()
    st = Stream()
    while True:
        try:
            st += GetLocalData(net, station, loc, chan, year, doy)
        except Exception as e:
            print(e)
        if year == end_year and doy == end_doy:
            #st.trim(starttime=starttime, endtime=endtime)
            return st
        doy += 1
        if doy >= 366:      # Allow leap years. OK if file doesn't exist.
            doy = 1
            year += 1

def MakeFilename(st, basename, extension):
    return "%s_%s_%s_%s_%s.%s" % (basename, net, station, loc, chan, extension)

def convert_raw_to_temperature(station, data):
    # Hack - different conversion factors for different digitizers
    if station == 'OMDBO':
        # For PSN-ADC24
        divider = 1.0           # for temperature channel
    else:
        # For seiscape2
        divider = 8.0       
    vref = 2.5                  # volts
    temp_scale_factor = 0.01    # volts / deg C (LM35)
    return data * vref * divider / temp_scale_factor / 2**23 


def convert_raw_to_voltage(station, data):
    # Hack - different conversion factors for different digitizers
    if station == 'OMDBO':
        # For PSN-ADC24
        divider = 17.0       
    else:
        # For seiscape2
        divider = 8.0       
    vref = 2.5                  # volts
    return data * vref * divider / 2**23 

def plot_temperature_and_cf(net, station, loc, chan_temp, chan_cf, starttime, endtime):
    # Read the response file containing the response data for this channel.         
    #response_file = '{}_{}.xml'.format(net, station)
    #inv = read_inventory(response_file)
    #print('inv:', inv[0][0][0].response)
                                          
    st_evc = GetLocalDataRange(net, station, loc, chan_cf, starttime, endtime)
    st_evc.merge()
    st_evc.trim(starttime=starttime, endtime=endtime)
    print(st_evc.__str__(extended=True))

    # This is extremely slow and PolynomialResponse not implemented yet, so
    # just manually convert to temperature.
    #st_evc.attach_response(inv)
    #st_evc.remove_response(inventory=inv)
    st_evc[0].data = convert_raw_to_voltage(station, st_evc[0].data)
    min_cf = min(st_evc[0].data)
    max_cf = max(st_evc[0].data)

    st_evt = GetLocalDataRange(net, station, loc, chan_temp, starttime, endtime)
    st_evt.merge()
    st_evt.trim(starttime=starttime, endtime=endtime)
    print(st_evt.__str__(extended=True))

    # LP filter the temperature to remove some noise.
    # Cannot filter if trace contains gaps (masked).
    if not np.ma.is_masked(st_evt[0].data):
        st_evt.filter('lowpass', freq=0.1, corners=8, zerophase=True) 
    st_evt.trim(starttime=starttime+200, endtime=endtime-200)   # remove filter startup effects

    # This is extremely slow and PolynomialResponse not implemented yet, so
    # just manually convert to temperature.
    #st_evt.attach_response(inv)
    #st_evt.remove_response(inventory=inv)
    st_evt[0].data = convert_raw_to_temperature(station, st_evt[0].data)
    min_temp = min(st_evt[0].data)
    max_temp = max(st_evt[0].data)
    hours = round((st_evt[0].stats.endtime - st_evt[0].stats.starttime) / 3600.0)

    # After merge we should have only one trace in each stream.
    tr_evt = st_evt[0]
    tr_evc = st_evc[0]

    fig, axes = plt.subplots(nrows=2, figsize=(12,7.5))
    fig.set_dpi(100)
    fig.autofmt_xdate()  # ticks slanted to allow for more room
    axes[0].plot(tr_evt.times('matplotlib'), tr_evt.data, color='r', label=tr_evt.id)
    axes[0].set_ylabel('Degrees C')
    axes[1].plot(tr_evc.times('matplotlib'), tr_evc.data, color='b', label=tr_evc.id)
    axes[1].set_ylabel('Volts')
    axes[0].legend(loc='upper left', handlelength=0)
    axes[1].legend(loc='upper left', handlelength=0)
    axes[0].xaxis_date()
    axes[1].xaxis_date()
    axes[0].grid(which='major')
    axes[1].grid(which='major')
    axes[0].grid(which='minor', linestyle='dashed')
    axes[1].grid(which='minor', linestyle='dashed')
    axes[0].xaxis.set_minor_locator(HourLocator(range(0, 25, 1)))
    axes[1].xaxis.set_minor_locator(HourLocator(range(0, 25, 1)))
    #fig.suptitle(r'$\bf{%s.%s.%s}$' % (net, station, loc) + '\n%d hour instrument temperature and centering force (range = %0.3f deg. C)' % 
        #(hours, max_temp-min_temp))
    fig.suptitle(
        r'$\bf{%s.%s.%s}$' % (net, station, loc) + 
        '\n%d hour instrument temperature (range: %0.3f deg. C) and centering force (range: %0.3f volts)' % 
        (hours, max_temp-min_temp, max_cf-min_cf))
    fig.savefig('daily_temperature_{}_{}_{}.png'.format(net, station, loc), bbox_inches='tight')

################################################################################

now = UTCDateTime()
starttime = now - 48*60*60
endtime = now
year = starttime._get_year()

# Two channels on each of two stations.
plot_temperature_and_cf('AM', 'OMDBO', '01', 'LKS', 'LEC', starttime, endtime)
plot_temperature_and_cf('AM', 'GBLCO', '01', 'EVT', 'EVC', starttime, endtime)

print("Done!")
exit(0)

