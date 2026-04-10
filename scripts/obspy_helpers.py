# Some common helper functions for using Obspy.

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
def GetLocalData(net, station, loc, chan, year=0, doy=0, path=None):
    try:
        if path is None:
            # Use the path to data on archive.local
            path = '/data/seismometer_data/mseed'
    
        fname = path + '/%s.%s.%s.%s.%d.%d.mseed' % (net, station, loc, chan, year, doy)
        #st = read('/data/seismometer_data/mseed/%s.%s.%s.%s.%d.%d.mseed' % (net, station, loc, chan, year, doy))
        st = read(fname)
        return st
    except:
        return None

# Read the station datafrom a local file, covering the timespan from startime to endtime.
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

# Get the station data from a Seedlink server.
def GetSeedlinkData(seedlink_addr, net, station, loc, chan, starttime, endtime):
    if ':' in seedlink_addr:
        host, port = seedlink_addr.rsplit(':', 1)
        port = int(port)
        client = SeedlinkClient(server=host, port=port)
    else:
        client = SeedlinkClient(seedlink_addr)

    st = client.get_waveforms(net, station, loc, chan, starttime, endtime)
    return st

# Use a temporary local file first, then retrieve any additional data needed from server.
def GetData(seedlink_addr, net, station, loc, chan, starttime, endtime):
    # Use a local temporary file in the current directory.
    st = GetLocalData(net, station, loc, chan, path='.')
    if st == None or len(st) == 0:
        print("Getting entire data from Seedlink server ", seedlink_addr)
        st = GetSeedlinkData(seedlink_addr, net, station, loc, chan, starttime,
                endtime)
    else:
        st.trim(starttime, endtime)
        if(len(st) == 0):
            # This will force a retrieval below.
            oldest = endtime
            newest = starttime 
        else:
            oldest = min([tr.stats.starttime for tr in st.traces]) 
            newest = max([tr.stats.endtime for tr in st.traces]) 
            print("Found local data from", oldest, "to", newest)
        if(oldest > starttime+1):
            print("Getting old data from", starttime, "to", oldest, 
                  "from Seedlink server", seedlink_addr)
            st2 = GetSeedlinkData(seedlink_addr, net, station, loc, chan, 
                                  starttime, oldest)
            print("Merging data...")
            st += st2
        if(newest < endtime):
            print("Getting latest data from", newest, "to", endtime, 
                  "from Seedlink server ", seedlink_addr)
            st2 = GetSeedlinkData(seedlink_addr, net, station, loc, chan, 
                                  newest, endtime)
            print("Merging data...")
            st += st2
    print('Gaps before merge:')
    st.print_gaps()
    st.merge(method=0, fill_value='interpolate')	# try to mitigate filter transients.
    print('Gaps after merge:')
    st.print_gaps()
    if len(st) > 0:
        print("Writing data to local file.")
        st.write('%s.%s.%s.%s.mseed' % (net, station, loc, chan), 
                 format='MSEED')
    return st

# Get data from IRIS
def GetIrisDataRange(net, station, loc, chan, starttime, endtime):
    client = FdsnClient("IRIS")
    st = client.get_waveforms(net, station, loc, chan, starttime, endtime)
    return st

def GetIrisResponse(net, station, loc, chan, starttime, endtime):
    client = FdsnClient("IRIS")
    inventory = client.get_stations(
        starttime=starttime, endtime=endtime,
        network=net, sta=station, loc=loc, channel=chan,
        level="response")
    return inventory

# Generate a filename specific to this stream's net, station, location, channel.
def MakeFilename(st, basename, extension):
    return "%s_%s_%s_%s_%s.%s" % (basename, net, station, loc, chan, extension)


# Get list of recent earthquakes.
def GetEvents(starttime, endtime, min_magnitude=0.0, provider=['IRIS', 'ISC', 'USGS']):
    events = []
    for provider in ['IRIS', 'ISC', 'USGS']:
        client = FdsnClient(provider)
        try:
            cat = client.get_events(starttime=starttime, endtime=endtime,
                                minmagnitude=min_magnitude)
            if len(cat.events) > 0:
                #print(cat.__str__(print_all=True))
                return cat
        except Exception as e:
            print('GetEvents: provider:', provider, e)
    return Catalog()        # empty

# Given a catalog of events, select events that match at least one of the filter
# critia. Each critera specifies a maximum distance for a minimum magnitude.
# filt is a list of tuples: (magnitude, distance), where distance (m) is 
# relative to lat, lon.
# Example: include this event if:
#   [ (4.0, 500*1000),      >= M4.0 within 500km
#     (5.0, 10000*1000),    >= M5.0 within 10000km
#     (6.0, 15000*1000),    >= M6.0 within 15000km
#     (7.0, inf) ]          >= M7.0 within any distance
def FilterEvents(events, filt, lat, lon):
    result = Catalog()
    for f in filt:
        magnitude = f[0]
        distance = f[1]
        accepted = [e for e in events \
                    if not e in result and \
                        e.magnitudes[0].mag >= magnitude and \
                        gps2dist_azimuth(lat, lon, e.origins[0].latitude, \
                            e.origins[0].longitude)[0] <= distance]
        for e in accepted:
            result.append(e)

    print("Events after filtering:")
    for e in result:
        (d, a, z) = gps2dist_azimuth(site[0], site[1], 
                        e.origins[0].latitude, e.origins[0].longitude)
        print("%s | Distance %.0f km, azimuth %d deg" % 
                (e.short_str(), d/1000, a))
    return result

# Helper to clean up obspy dayplot.
def FixupAnnotations(fig):
    annotations = [child for child in fig.axes[0].get_children() 
        if isinstance(child, plt.text.Annotation)]

    # Change size of annotation text
    for a in annotations:
        a.set_fontsize('xx-small')

    # If any are overlapping, push them around
    for i in range(len(annotations)):
        yloc = []
        for a in annotations:
            y = a.xyann[1]
            if y in yloc:
                y -= 1.0
                print('moving down from %f to %f' % (a.xyann[1], y))
            a.xyann = (a.xyann[0], y)
            yloc.append(y)

# Make a helicorder plot and save to file.
def Helicorder(stream, filename, location, starttime, duration, freqmin=0,
	freqmax=0, decimation=1, scale=None, events={}):
    print("Plotting helicorder ", filename)
    plt.rc('text', usetex=True)     # use LaTex tags
    st = stream.copy()
    timefmt = "%H:%M UTC"
    if(scale and scale < 1e-6):
        scale_str = "%.0f nm/sec per line" % (scale*1e9)
        scaling = scale / units
    elif(scale and scale < 1e-3):
        scale_str = "%.0f µm/sec per line" % (scale*1e6)
        scaling = scale / units
    elif(scale and scale < 1):
        scale_str = "%.0f mm/sec per line" % (scale*1e3)
        scaling = scale / units
    else:
        scale_str = "unknown"
        scaling = None

    filter_str = ''
    if freqmin != 0:
        filter_str += 'HP=%.1g Hz' % freqmin
    if freqmin != 0 and freqmax != 0:
        filter_str += ' '
    if freqmax != 0:
        if freqmax < 1:
            filter_str += 'LP=%.2f Hz' % freqmax
        else:
            filter_str += 'LP=%.1f Hz' % freqmax
    if freqmin != 0 or freqmax != 0:
        filter_str += '. '

    title = '%s' % st[0].id
    subtitle = '%s. %s. Yuma-2 v4.0. %sScale %s.' % \
        (starttime.date, location, filter_str, scale_str)
    titlestr = r'\begin{center}{\textbf{%s\\}}%s\end{center}' % \
        (title, subtitle)

    if(freqmin != 0 and freqmax != 0):
	# Obspy docs say data should be detrended before filtering to avoid
	# 'massive artifacts'.
        st.detrend(type='demean')
        #st.detrend(type='simple')

        #st.filter("bandpass", freqmin=freqmin, freqmax=freqmax, corners=4, 
            #zerophase=True)
	# Use 2nd order HP and 8th order LP to match filter done in WinSDR.
        st.filter("highpass", freq=freqmin, corners=2, zerophase=True)
        st.filter("lowpass", freq=freqmax, corners=8, zerophase=True)
    if(decimation > 1):
        st.decimate(decimation, no_filter=True)

    fig = st.plot(type='dayplot', dpi=200, linewidth=0.15, 
            vertical_scaling_range=scaling, size=(1600,1200), interval=60, 
            handle=True, number_of_ticks=7, 
            starttime=starttime, endtime=starttime+duration,
            right_vertical_labels=False, one_tick_per_line=True, 
            show_y_UTC_label=False, tick_format=timefmt, title=titlestr, 
            subplots_adjust_top=0.93, subplots_adjust_bottom=0.05,
            subplots_adjust_left=0.1, subplots_adjust_right=0.98, 
            events=events)

    fig.axes[0].set_xlabel('')

    # Add any other drawing here.
    FixupAnnotations(fig)

    # Make event markers semi-transparent yellow.
    ax = fig.gca()
    for l in ax.lines:
        l._markerfacecolor = (1, 1, 0, 0.7)
        l._markeredgecolor = (1, 1, 0, 0.5)

    fig.canvas.draw()
    fig.savefig(filename, bbox_inches='tight')
    #fig.savefig(filename)
    plt.pyplot.clf()
    plt.pyplot.close(fig)

# Make a spectrogram plot and save to file.
def Spectrogram(stream, filename, starttime, duration, title=None, freqmin=0, 
        freqmax=0, decimation=1, per_lap=0.95, wlen=300.0, vline=None):
    print("Plotting spectrogram ", filename)
    st = stream.copy()
    # Filter first, then slice, to minimize filter startup transient.
    if freqmin != 0:
        st.filter("highpass", freq=freqmin, corners=2, zerophase=True)
    if freqmax != 0:
        st.filter("lowpass", freq=freqmax, corners=8, zerophase=True)
    st = st.slice(starttime=starttime, endtime=starttime+duration)
    if(st == None or len(st) == 0):
        return      # no data to plot
    if(decimation > 1):
        st.decimate(decimation, no_filter=True)

    plt.rc('text', usetex=True)     # use LaTex tags
    title_str = '%s' % st[0].id
    subtitle = ''
    if(title):
        subtitle += title + r'\\'
    subtitle += 't0 = ' + str(st[0].stats.starttime)
    title_str = r'\begin{center}{\textbf{%s\\}}%s\end{center}' % \
        (title_str, subtitle)

    # Don't plot to file immediately. Set the ylimit and title manually.
    fig = st.spectrogram(log=False, per_lap=per_lap, wlen=wlen, dbscale=False,
        clip=[0, 0.05], show=False)
    fig = fig[0]
    ax = fig.axes[0]
    if freqmax != 0:
        ax.set_ylim(0, freqmax)
    ax.set_xlim(wlen/2, duration-wlen/2)
    ax.set_title(title_str, wrap=True)
    if vline != None:
        ax.axvline(x=vline, ls=(0, (5, 10)), color='white', lw=0.8, 
            label='Expected arrival')
        ax.legend(loc='upper right')
    fig.canvas.draw()
    fig.savefig(filename, bbox_inches='tight')
    plt.pyplot.clf()
    plt.pyplot.close(fig)

# Use the earth model to estimate arrival times of events.
# Returns (event_time, desc, first_arrival, arrival_rayleigh)[]
def GetArrivalTimes(events):
    event_time = []
    arrival_first = []
    arrival_rayleigh = []
    desc = []
    for e in events:
        if e.origins[0].depth == None or e.origins[0].longitude == None or \
           e.origins[0].latitude == None:
            continue
        model = TauPyModel()
        arrivals = model.get_travel_times_geo(e.origins[0].depth/1000,
                e.origins[0].latitude, e.origins[0].longitude, site[0], site[1],
                phase_list=["P", "S"])
        (d, a, z) = gps2dist_azimuth(site[0], site[1],
                        e.origins[0].latitude, e.origins[0].longitude)
        event_time.append(e.origins[0].time)
        # First arrival of any phase (taup returns sorted by time).
        first_time = arrivals[0].time if arrivals else 0
        arrival_first.append(e.origins[0].time + first_time)
        # Rayleigh travel time approxmately 4.0 km/sec
        arrival_rayleigh.append(e.origins[0].time + d/1000 / 4.0)
        desc.append('%s, %.1f %s, %.0f km away' %
                (e.event_descriptions[0].text, e.magnitudes[0].mag,
                e.magnitudes[0].magnitude_type, d/1000))
    return zip(event_time, desc, arrival_first, arrival_rayleigh)

## Use the earth model to estimate arrival times of event.
## Returns array of (event, desc, times[])
#def GetAllArrivalTimes(event, site):
#    event_time = []
#    arrival_times = []
#    arrival_rayleigh = []
#    desc = []
#    for e in events:
#        if e.origins[0].depth == None or e.origins[0].longitude == None or \
#           e.origins[0].latitude == None:
#            continue
#        model = TauPyModel()
#        arrivals = model.get_travel_times_geo(e.origins[0].depth/1000, 
#                e.origins[0].latitude, e.origins[0].longitude, site[0], site[1], 
#                phase_list=["P", "S"])
#        print('arrivals:', arrivals)
#        (d, a, z) = gps2dist_azimuth(site[0], site[1], 
#                        e.origins[0].latitude, e.origins[0].longitude)
#        #print("Arrivals for event ", e)
#        #print(arrivals)
#        #print("Phase " + arrivals[0].name + " at " + str(arrivals[0].time))
#        # There may be multiple P and multiple S for a single quake.
#        event_time.append(e.origins[0].time)
#        arrival_times.append(e.origins[0].time + min([0] or [a.time for a in arrivals]))
#        # Rayleigh travel time approxmately 4.0 km/sec
#        arrival_rayleigh.append(e.origins[0].time + d/1000 / 4.0)
#        desc.append('%s, %.1f %s, %.0f km away' % 
#                (e.event_descriptions[0].text, e.magnitudes[0].mag, 
#                e.magnitudes[0].magnitude_type, d/1000))
#    return zip(event_time, desc, arrival_times, arrival_rayleigh)

# Use the earth model to estimate arrival times of one event.
def GetAllArrivalTimes(event, site):
    if event.origins[0].depth == None or \
        event.origins[0].longitude == None or \
        event.origins[0].latitude == None:
            return None
    else:
        model = TauPyModel()
        arrivals = model.get_travel_times_geo(
                event.origins[0].depth/1000, 
                event.origins[0].latitude, 
                event.origins[0].longitude, 
                site[0], site[1])
                #phase_list=["P", "S"])
        (d, a, z) = gps2dist_azimuth(site[0], site[1], 
                        event.origins[0].latitude, event.origins[0].longitude)

        # There may be multiple P and multiple S for a single quake.
        for a in arrivals:
            print("Phase " + a.name + " at " + str(a.time))

        event_time = event.origins[0].time

        # Rayleigh travel time approxmately 4.0 km/sec
        arrival_rayleigh = event.origins[0].time + (d/1000 / 4.0)
        desc = ("%s, %.1f %s, %.0f km away" % 
                (event.event_descriptions[0].text, event.magnitudes[0].mag, 
                event.magnitudes[0].magnitude_type, d/1000))
    return event_time, desc, arrivals, arrival_rayleigh

################################################################################

# This hack is a direct way to convert raw values to temperature.
def convert_raw_to_temperature(station, data):
    # Hack - different conversion factors for different digitizers
    if station == 'OMDBO' or station == 'BCCWA':
        # For PSN-ADC24
        divider = 1.0           # for temperature channel
    else:
        # For seiscape2
        divider = 8.0       
    vref = 2.5                  # volts
    temp_scale_factor = 0.01    # volts / deg C (LM35)
    return data * vref * divider / temp_scale_factor / 2**23 

# This hack is a direct way to convert raw values to voltage.
def convert_raw_to_voltage(station, data):
    # Hack - different conversion factors for different digitizers
    if station == 'OMDBO' or station == 'BCCWA':
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

# Return a list of velocity PSD values (period / value) for the NLNM and NHNM.
def get_nlnm_nhnm_velocity():

    # Velocity PSD of the USGS New low noise model 
    # dB relative to (1 m/s)^2/Hz
    # from
    # http://gfzpublic.gfz-potsdam.de/pubman/item/escidoc:4017:4/component/escidoc:4018/Chapter_4_rev1.pdf
    # period, velocity noise
    nlnm_vel =  	[(0.1, -203.9), (0.17, -198.1), (0.4, -190.6), (0.8, -187.1), (1.24, -177.8),
             (2.40, -157.0), (4.3, -144.4), (5.0, -143.1), (6.0, -149.4), (10.0, -159.7),
             (12.0, -160.6), (15.6, -154.2), (21.9, -166.7), (31.6, -171.0), (45.0, -170.4),
             (70.0, -166.6), (101.0, -160.9), (154.0, -157.2), (328.0, -153.1), (600.0, -144.8),
             (10000, -87.9), (100000, -19.1)]

    # Velocity PSD of the USGS New high noise model 
    # dB relative to (1 m/s)^2/Hz
    # from
    # http://gfzpublic.gfz-potsdam.de/pubman/item/escidoc:4017:4/component/escidoc:4018/Chapter_4_rev1.pdf
    # period, velocity noise
    nhnm_vel =  	[(0.1, -127.5), (0.22, -126.5), (0.32, -136.4), (0.80, -137.9), (3.80, -102.4),
             (4.60, -99.2), (6.3, -101.0), (7.9, -111.5), (15.4, -112.2), (20.0, -128.4),
             (354.8, -91.0), (10000, -16.1), (100000, 35.5)]

    return nlnm_vel, nhnm_vel

# Return a list of acceleration PSD values (period / value) for the NLNM and NHNM.
def get_nlnm_nhnm_acceleration():

    # Acceleration PSD of the USGS New low noise model 
    # dB relative to (1 m/s^2)^2/Hz
    # from
    # http://gfzpublic.gfz-potsdam.de/pubman/item/escidoc:4017:4/component/escidoc:4018/Chapter_4_rev1.pdf
    # period, velocity noise
    nlnm_accel =  [(0.1, -168.0), (0.17, -166.7), (0.4, -166.7), (0.8, -169.2), (1.24, -163.7),
         (2.40, -148.6), (4.3, -141.1), (5.0, -141.1), (6.0, -149.0), (10.0, -163.8),
         (12.0, -166.2), (15.6, -162.1), (21.9, -177.5), (31.6, -185.0), (45.0, -187.5),
         (70.0, -187.5), (101.0, -185.0), (154.0, -185.0), (328.0, -187.5), (600.0, -184.4),
         (10000, -151.9), (100000, -103.1)]

    # Acceleration PSD of the USGS New high noise model 
    # dB relative to (1 m/s^2)^2/Hz
    # from
    # http://gfzpublic.gfz-potsdam.de/pubman/item/escidoc:4017:4/component/escidoc:4018/Chapter_4_rev1.pdf
    # period, velocity noise
    nhnm_accel =  [(0.1, -91.5), (0.22, -97.4), (0.32, -110.5), (0.80, -120.0), (3.80, -98.0),
         (4.60, -96.5), (6.3, -101.0), (7.9, -113.5), (15.4, -120.0), (20.0, -138.5),
         (354.8, -126.0), (10000, -80.1), (100000, -48.5)]

    return nlnm_accel, nhnm_accel
