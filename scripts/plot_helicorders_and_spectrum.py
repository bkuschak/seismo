# Read data from Seedlink server and generate helicorder and spectrogram plots.

from obspy.clients.seedlink.basic_client import Client as SeedlinkClient
from obspy.clients.seedlink.easyseedlink import create_client
from obspy.clients.fdsn import Client as FdsnClient
from obspy.geodetics.base import gps2dist_azimuth
from obspy.core.event import Catalog
from obspy.core.stream import Stream
from obspy.taup.tau import TauPyModel
from obspy import UTCDateTime
from obspy import read
import matplotlib as plt
import gc

################################################################################

# For plot annotations.
location = 'Bend, OR'

# Server to query and data to plot.
seedlink_server = 'archive.local'
net = 'AM'
station = 'OMDBO'
loc = '01'
chan = 'BHZ'

# If local data is older than this in seconds, retrieve new data from the server.
age_limit = 120*60

# Units per LSB. FIXME - Get this from dataless SEED if possible?
units = 1.88e-9		# input data scale m/s per LSB.

# Helicorder scale on the plot.
scale_broadband_helicorder_line = 30e-6         # m/s 
scale_teleseismic_helicorder_line = 300e-9      # m/s 

# Latitude and longitude of the our location
# FIXME - get this from dataless SEED?
site = (44.0464, -121.3151)

################################################################################

# Get the station data from Seedlink server.
def GetSeedlinkData(seedlink_addr, net, station, loc, chan, starttime, endtime):
    client = SeedlinkClient(seedlink_addr)
    st = client.get_waveforms(net, station, loc, chan, starttime, endtime)
    #st.write('%s.%s.%s.%s.mseed' % (net, station, loc, chan), format='MSEED')
    return st

# Read the station data from a local file.
def GetLocalData(net, station, loc, chan):
    try:
        st = read('%s.%s.%s.%s.mseed' % (net, station, loc, chan))
        return st
    except:
        return None

# Use local data first, then retrieve any additional data needed from server.
def GetData(seedlink_addr, net, station, loc, chan, starttime, endtime):
    st = GetLocalData(net, station, loc, chan)
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
    st.merge(method=0, fill_value=0)
    if len(st) > 0:
        print("Writing data to local file.")
        st.write('%s.%s.%s.%s.mseed' % (net, station, loc, chan), 
                 format='MSEED')
    return st

# Get list of recent earthquakes.
def GetEvents(provider, starttime, endtime, min_magnitude):
    client = FdsnClient(provider)
    try:
        cat = client.get_events(starttime=starttime, endtime=endtime,
                            minmagnitude=min_magnitude)
        return cat
    except:
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
        st.filter("bandpass", freqmin=freqmin, freqmax=freqmax, corners=4, 
            zerophase=True)
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
    if(freqmin != 0 and freqmax != 0):
        st.filter("bandpass", freqmin=freqmin, freqmax=freqmax, corners=4, 
            zerophase=True)
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
    # FIXME
    fig = st.spectrogram(log=False, per_lap=per_lap, wlen=wlen, dbscale=False, 
    #fig = st.spectrogram(log=False, dbscale=False, 
        show=False)
    fig = fig[0]
    ax = fig.axes[0]
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

def MakeFilename(st, basename, extension):
    return "%s_%s_%s_%s_%s.%s" % (basename, net, station, loc, chan, extension)

# Use the earth model to estimate arrival times of events.
# Returns (desc, time_p, time_s)[]
def GetArrivalTimes(events):
    event_time = []
    arrival_p = []
    arrival_s = []
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
        #print("Arrivals for event ", e)
        #print(arrivals)
        #print("Phase " + arrivals[0].name + " at " + str(arrivals[0].time))
        # There may be multiple P and multiple S for a single quake.
        event_time.append(e.origins[0].time)
        arrival_p.append(e.origins[0].time + 
            min([0] or [a.time for a in arrivals if a.name == 'P']))
        arrival_s.append(e.origins[0].time + 
            min([0] or [a.time for a in arrivals if a.name == 'S']))
        # Rayleigh travel time approxmately 4.0 km/sec
        arrival_rayleigh.append(e.origins[0].time + d/1000 / 4.0)
        desc.append('%s, %.1f %s, %.0f km away' % 
                (e.event_descriptions[0].text, e.magnitudes[0].mag, 
                e.magnitudes[0].magnitude_type, d/1000))
    return zip(event_time, desc, arrival_p, arrival_s, arrival_rayleigh)

################################################################################

# Start 24 hours from the most recent hour boundary
#now = UTCDateTime("2022-01-16T00:00:00.0")
now = UTCDateTime()
starttime = now - 23*60*60
starttime -= (starttime.second + 60*starttime.minute)
endtime = now
print("Plotting data from startime:", starttime, "to endtime:", endtime)

print("Attempting to retrieve Seedlink data from:", seedlink_server)
print(net, station, loc, chan)
st = GetData(seedlink_server, net, station, loc, chan, starttime, endtime)
print("Got some data")
latest = max([tr.stats.endtime for tr in st.traces])
print(st.__str__(extended=True))

# If traces have gaps or overlaps, Maybe do something like:
#if np.any(np.isnan(data)):
#    data = np.ma.masked_invalid(data)
#    data = np.ma.filled(data, fill_value=0)
#st.plot(show=True)
#st.merge(fill_value=0)
##st.merge()
#print(st)
#st.plot(show=True)

# Don't warn about figures.
plt.rcParams.update({'figure.max_open_warning': 0})

# First plot un-annotated helicorder plots of the complete data set.
# Note: Decimation results in scaling error across each line. Larger factors
# result in data delayed in time, even if sps remains integer. So don't 
# decimate.
Helicorder(st, MakeFilename(st, 'helicorder_teleseismic', 'png'), 
    location, starttime, 86400, freqmin=0.005, freqmax=0.07, decimation=1, 
    scale=scale_teleseismic_helicorder_line)

Helicorder(st, MakeFilename(st, 'helicorder_broadband', 'png'), 
    location, starttime, 86400, freqmin=0.002, freqmax=25, decimation=1,
    scale=scale_broadband_helicorder_line)

# Get earthquake events during this time. Try multiple providers if necessary.
for provider in ['IRIS', 'ISC', 'USGS']:
    all_events = GetEvents(provider, starttime, endtime, 2.0)
    if len(all_events.events) > 0:
        break
print("All events:")
print(all_events.__str__(print_all=True))

# Filter quakes that we care about for the broadband plot:
filt = [ (2.0, 10*1000), (3.0, 100*1000), (4.0, 500*1000), (5.0, 5000*1000), 
        (6.0, 10000*1000), (7.0, float('inf')) ]
broadband_events = FilterEvents(all_events, filt, site[0], site[1])
for e in broadband_events:
    (d, a, z) = gps2dist_azimuth(site[0], site[1], e.origins[0].latitude, 
            e.origins[0].longitude)
    print("Broadband: %s | Distance %.0f km, azimuth %d deg" % 
        (e.short_str(), d/1000, a))

# Filter quakes that we care about for the teleseismic plot:
filt = [ (4.0, 8000*1000), (4.5, 12000*1000), (5.0, 15000*1000), 
         (6.0, float('inf')) ]
teleseismic_events = FilterEvents(all_events, filt, site[0], site[1])
for e in teleseismic_events:
    (d, a, z) = gps2dist_azimuth(site[0], site[1], e.origins[0].latitude, 
            e.origins[0].longitude)
    print("Teleseismic: %s | Distance %.0f km, azimuth %d deg" % 
        (e.short_str(), d/1000, a))

# Plot the helicorder plots annotated with events.
# Note: Decimation results in scaling error across each line. Larger factors
# result in data delayed in time, even if sps remains integer. So don't 
# decimate.
Helicorder(st, MakeFilename(st, 'helicorder_broadband_annotated', 'png'), 
    location, starttime, 86400, freqmin=0.002, freqmax=25, 
    scale=scale_broadband_helicorder_line, events=broadband_events)

Helicorder(st, MakeFilename(st, 'helicorder_teleseismic_annotated', 'png'), 
    location, starttime, 86400, freqmin=0.005, freqmax=0.07, decimation=1, 
    scale=scale_teleseismic_helicorder_line, events=teleseismic_events)

# Spectrograms for the broadband and teleseismic events. 
print("Broadband arrivals:")
broadband_arrivals = GetArrivalTimes(broadband_events)
for t,desc,p,s,r in broadband_arrivals:
    print("P, S for event: " + str(p) + ", " + str(s));
    # Only plot if we have enough data. Plot from 10 minutes before the p-wave
    # to 'duration' seconds after.
    duration = 1800
    if (latest-p) >= duration:
        timestr = str(p).replace(':', '_')
        #Spectrogram(st, "spectrum_broadband_%s.png" % timestr, p-600, 
        Spectrogram(st, MakeFilename(st, 'spectrum_broadband_%s' % timestr, 
            'png'), p-600, duration+600, freqmin=0.002, freqmax=25, decimation=1, 
            title=desc, vline=r-p-600)

# Spectrograms for the teleseismic events. 
print("Teleseismic arrivals:")
teleseismic_arrivals = GetArrivalTimes(teleseismic_events)
for t,desc,p,s,r in teleseismic_arrivals:
    print("P, S for event", desc, str(p) + ", " + str(s));
    # Only plot if we have an hour's worth of data after the event. Plot from
    # the p-wave arrival until 'duration' seconds after.
    duration = 2*3600 
    if (latest-p) >= 3600:
        timestr = str(p).replace(':', '_')
        #Spectrogram(st, "spectrum_teleseismic_%s.png" % timestr, p, duration,
        Spectrogram(st, MakeFilename(st, 'spectrum_teleseismic_%s' % timestr, 'png'), p, duration,
            #freqmin=0.002, freqmax=0.09, decimation=65, title=desc, vline=r-p, wlen=600, per_lap=0.99)
            #freqmin=0.002, freqmax=0.09, decimation=400, title=desc, vline=r-p, wlen=600, per_lap=0.999)
            freqmin=0.002, freqmax=0.09, decimation=800, title=desc, vline=r-p,
            wlen=600, per_lap=0.999999)

# Broadband spectrogram for entire day.
Spectrogram(st, MakeFilename(st, 'spectrum_broadband_all_day', 'png'), 
    starttime, endtime-starttime, freqmin=0.002, freqmax=25.0, decimation=4, 
    title='All day', wlen=30.0, per_lap=0.5)

print("Done!")
exit(0)

