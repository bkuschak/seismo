# Plot waveforms.

import argparse
import dateutil
from obspy import UTCDateTime
from obspy.core.inventory import Inventory, Network, Station, Channel, Site
from matplotlib.dates import HourLocator, MinuteLocator, SecondLocator

import sys
sys.path.append('.')
from  obspy_helpers import *

################################################################################

#site = (44.0464, -121.3151)     # OMDBO
site = (43.50999, -120.24793)   # GBLCO

# Defaults
path = '/data/seismometer_data/mseed'
outfile = 'event.png'
dpi = 150

# Parse command line arguments.
desc = \
'''
Generate seismic plot covering a certain time period.
  Methods:
    1) specify --starttime and --endtime.
    2) specify --eventtime and --event_search_time. Optionally --before_event and --after_event.

  May specify multiple channels.

Example: python %s --channel "AM.OMDBO.01.BHZ" --starttime "2024-07-31T04:30:00"
''' % (sys.argv[0])

parser = argparse.ArgumentParser(description=desc,
    formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--width', type=int, default=1400,
    help='Width of plot in pixels.')
parser.add_argument('--height', type=int, default=600,
    help='Height of plot in pixels.')
#parser.add_argument('--segment_len', type=int, dest='segment_len',
    #default=segment_len, help='Length of time in seconds for each segment.')
#parser.add_argument('--segment_overlap', type=float, dest='segment_overlap',
    #default=segment_overlap, help='Overlap of segments, from 0.001 to 0.999.')
parser.add_argument('--path', dest='path', default=path,
    help='Path to the directory of the MiniSEED files.')
#parser.add_argument('--respfile', dest='response_file', default=response_file,
	#help='StationXML response definition file (default is {})'.
    #format(response_file))
#parser.add_argument('--infile', dest='infile', default=None,
	#help='MiniSEED input filename')
parser.add_argument('--outfile', dest='outfile', default=outfile,
	help='Output filename (default is {}).'.format(outfile))
parser.add_argument('--dpi', type=int, default=dpi,
    help='Pixels per inch ({} default).'.format(dpi))

parser.add_argument('--lowpass', type=float, dest='lowpass',
    default=None, help='Low-pass filter corner frequency.')
parser.add_argument('--highpass', type=float, dest='highpass',
    default=None, help='High-pass filter corner frequency.')

parser.add_argument('--starttime', dest='starttime', default=None,
	help='Start time of the data. Ex: 4/25/15 00:00 UTC')
parser.add_argument('--endtime', dest='endtime', default=None,
	help='End time of the data. Ex: 4/26/15 00:00 UTC')

parser.add_argument('--eventtime', dest='eventtime', default=None,
	help='Approximate time of the event. Ex: 4/26/15 00:00 UTC')
parser.add_argument('--before', type=float, dest='before', default=60,
	help='Plot this number of seconds before the first event arrival.')
parser.add_argument('--after', type=float, dest='after', default=5*60,
	help='Plot this number of seconds after the first event arrival.')
parser.add_argument('--search_time', type=float, dest='search_time', default=60,
	help='Duration in seconds before and after the event to use when searching the event catalog.')
parser.add_argument('--min_magnitude', type=float, dest='min_magnitude', default=3.0,
	help='Minimum magnitude to use when searching the event catalog.')

parser.add_argument('--channel', action='append', dest='channel', default=None,
    help='NETWORK.STATION.LOCATION.CHANNEL format. Multiple channels may be specified.')
parser.add_argument('--deconvolve', dest='deconvolve', action='store_true', 
    help='Deconvolve to remove the instrument response.')

#parser.add_argument('--show', action='count', default=None,
    #help='Show the plot interactively.')
parser.add_argument('-v', '--verbose', action='count',
    help='Increase verbosity.')
args = parser.parse_args()

arrivals = None
deconvolved = False

if args.verbose:
	print(args)

if args.starttime and args.endtime:
    starttime = UTCDateTime(dateutil.parser.parse(args.starttime))
    endtime = UTCDateTime(dateutil.parser.parse(args.endtime))

elif args.eventtime:
    search_eventtime = UTCDateTime(dateutil.parser.parse(args.eventtime))
    start = search_eventtime - args.search_time
    stop  = search_eventtime + args.search_time

    # Find events in this time window.
    events = GetEvents(start, stop, args.min_magnitude)
    if events is None or len(events) == 0:
        print('No events found near', search_eventtime)
        exit(0)
    print('{} events found:'.format(len(events)))
    print(events.__str__(print_all=True))

    # Choose the event with the largest magnitude.
    # FIXME

    # Get all the arrivals for this event. Choose the earliest.
    # FIXME - these will be specific to one site. Make one per site.
    # FIXME - get site from the channel response data instead.
    eventtime, desc, arrivals, arrival_rayleigh  = GetAllArrivalTimes(events[0], site)
    earliest = min([a.time for a in arrivals])

    starttime = eventtime + earliest - args.before
    endtime = eventtime + earliest + args.after

else:
    print('Must specify either (--starttime and --endtime) or --eventtime.')
    exit(1)

print("Using data from startime:", starttime, "to endtime:", endtime)

# Add channels.
if args.channel is None or len(args.channel) == 0:
    print('Must provide at least one --channel.')
    exit(1)

# Read the channel data.
st = Stream()
for c in args.channel:
    # Format is like this: AM_GBLCO_01_BHZ
    net, station, loc, chan = c.split('.')

    # Use local files for our known channels.
    if net == 'AM' and station in ['OMDBO', 'GBLCO']:
        st += GetLocalDataRange(net, station, loc, chan, starttime, endtime)

        # GBLCO appears to be inverted. Fix that.
        if station == 'GBLCO' and chan == 'BHZ':
            for t in st:
                t.data = t.data * -1.0
    else:
        # Try to get the data from IRIS.
        st += GetIrisDataRange(net, station, loc, chan, starttime, endtime)


# Clean up the trace(s).
st.merge(method=0, fill_value='interpolate')
st.trim(starttime=starttime, endtime=endtime)
st = st.detrend()
print('Streams:\n', st.__str__(extended=True))

# Read the instrument response and deconvolve:
inv = None
deconvolved_str = ''
if args.deconvolve:
    inv = Inventory()
    for c in args.channel:
        # Format is like this: AM_GBLCO_01_BHZ
        net, station, loc, chan = c.split('.')
        got_resp = False

        # Try reading from local file first.
        try:
            fname = '{}_{}.xml'.format(net, station)
            inv += read_inventory(fname)
            print('Read instrument response from local file:', fname)
            got_resp = True
        except Exception as e:
            print('While trying to read response file:', e)

        # Try getting from IRIS.
        if not got_resp:
            try:
                print('Trying to read instrument response for {}.{}.{}.{} from IRIS.'.format(net, station, loc, chan))
                inv += GetIrisResponse(net, station, loc, chan, starttime, endtime)
                got_resp = True
                print('Read instrument response for {}.{}.{}.{} from IRIS.'.format(net, station, loc, chan))
                fname = '{}_{}.xml'.format(net, station)
                inv.write(fname, format='STATIONXML')
                print('Wrote instrument response to local file:', fname)
            except Exception as e:
                print('While trying to getting response file from IRIS:', e)

    # Deconvolve.
    # FIXME - bandpass to avoid adding noise due to deconvolution?
    for s in st:
        try:
            print('Removing instrument response for', s.id, '...')
            s.remove_response(inventory=inv)
            deconvolved = True
            deconvolved_str = 'Response removed. '
        except Exception as e:
            print('Failed removing instrument response for', s.id)

# Filter the data.
filter_str = ''
if args.highpass is not None:
    print('Applying high pass filter...')
    st.filter('highpass', freq=args.highpass, corners=4, zerophase=True)
    filter_str = 'HP={:.2f} Hz. '.format(args.highpass)
if args.lowpass is not None:
    print('Applying low pass filter...')
    st.filter('lowpass', freq=args.lowpass, corners=4, zerophase=True)
    filter_str += 'LP={:.2f} Hz. '.format(args.lowpass)

# Try to remove the filtering transients
starttrim = 0
endtrim = 0
if args.deconvolve:
    starttrim = 360
    endtrim = 200
elif args.lowpass or args.highpass:
    starttrim = 180
    endtrim = 180
if starttrim != 0 or endtrim != 0:
    print('Trimming the stream to remove filter transients')
    st.trim(starttime=starttime+starttrim, endtime=endtime-endtrim)

# Plot
print('Plotting streams as {}:\n'.format(outfile), st.__str__(extended=True))
fig = st.plot(show=False, size=(args.width,args.height), equal_scale=False, linewidth=1.0, color='blue')
ax = fig.gca()
if arrivals:
    for a in arrivals:
        t = eventtime + a.time
        name = str(a.name)
        for ax in fig.axes:
            ax.axvline(t.datetime, linestyle='--', label=name, alpha=0.5, linewidth=0.5, color = next(ax._get_lines.prop_cycler)['color'])
            ax.grid(which='minor', linestyle='dashed')
            ax.grid(which='major')
            #ax.xaxis.set_minor_locator(SecondLocator(range(0, 60, 10)))
            #ax.xaxis.set_major_locator(MinuteLocator(range(0, 60, 1)))
    title_str = desc + '\nEvent time: ' + eventtime.datetime.isoformat() + '. '
    title_str += filter_str + deconvolved_str
    #fig.suptitle(desc + '\nEvent time: ' + eventtime.datetime.isoformat())
    fig.suptitle(title_str)
    ax.legend(loc='upper right')

if deconvolved:
    for ax in fig.axes:
        ax.set_ylabel('m/sec')
else:
    for ax in fig.axes:
        ax.set_ylabel('counts')

fig.savefig(outfile)
exit(0)
