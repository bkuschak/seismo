# Plot probabilistic PSD of velocity using a miniseed input file.

import argparse
from datetime import datetime, timedelta
import dateutil
import matplotlib.pylab as plt
import matplotlib.mlab as mlb
import numpy as np
from obspy import read, read_inventory, Stream, UTCDateTime
from obspy.clients.seedlink.basic_client import Client as SeedlinkClient
from obspy.io.xseed import Parser
from obspy.signal import PPSD
import os
import pylab as pyl
import scipy as sy
import scipy.fftpack as syfp
import sys

sys.path.append('.')
from  obspy_helpers import *

# Defaults
width = 1200
height = 1000
outfile = 'ppsd.png'
response_file = 'station.xml'
path = '.'
segment_len = 7200
segment_overlap = 0.5
dpi = 150

# Parse command line arguments.
desc = \
'''
Generate plot of probabilistic power spectral density using MiniSEED data.\n\r
Unless otherwise specified plot the most recent 24 hours of data.\n\r
\n\r
Example: python %s --channel "AM.OMDBO.01.BHZ" 
''' % (sys.argv[0])

parser = argparse.ArgumentParser(description=desc, 
    formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--width', type=int, default=width, 
    help='Width of plot in pixels.')
parser.add_argument('--height', type=int, default=height, 
    help='Height of plot in pixels.')
parser.add_argument('--segment_len', type=int, dest='segment_len', 
    default=segment_len, help='Length of time in seconds for each segment.')
parser.add_argument('--segment_overlap', type=float, dest='segment_overlap', 
    default=segment_overlap, help='Overlap of segments, from 0.001 to 0.999.')
parser.add_argument('--path', dest='path', default=path, 
    help='Path to the directory of the MiniSEED files.')
parser.add_argument('--respfile', dest='response_file', default=response_file, 
	help='StationXML response definition file (default is {})'.
    format(response_file))
parser.add_argument('--server', dest='server', default=None,
    help='Use Seedlink server:port instead of a file')
parser.add_argument('--iris', dest='iris', action='store_true',
	help='Get data from IRIS. Mutually exclusive with --server.')
parser.add_argument('--infile', dest='infile', default=None,
	help='MiniSEED input filename')
parser.add_argument('--outfile', dest='outfile', default=outfile, 
	help='Output filename (default is {}).'.format(outfile))
parser.add_argument('--dpi', type=int, default=dpi, 
    help='Pixels per inch ({} default).'.format(dpi))
parser.add_argument('--starttime', dest='starttime', default=None, 
	help='Start time of the data. Ex: 4/25/15 00:00 UTC')
parser.add_argument('--endtime', dest='endtime', default=None, 
	help='End time of the data. Ex: 4/26/15 00:00 UTC')
parser.add_argument('--channel', dest='channel', default=None, 
    help='NETWORK.STATION.LOCATION.CHANNEL format.')
parser.add_argument('--show', action='count', default=None, 
    help='Show the plot interactively.')
parser.add_argument('-v', '--verbose', action='count', 
    help='Increase verbosity.')
parser.add_argument('--rotate', type=int, default=None,
    help='Rotate output files and keep this number of old copies.')
args = parser.parse_args()

if args.verbose:
	print(args)

if not args.channel:
    print('Must supply the --channel parameter.');
    exit(1)

# If a filename is selected, open it directly.
# Otherwise, open filenames based on the channel name and start/end times.
if args.infile:
    fname = args.path + '/' + args.infile
    print('Attempting to open file "{}"...'.format(fname))
    st = read(fname)
else:
    if args.starttime and args.endtime:
        # Nice little utility, recognizes time strings.
        # Specific start and end times.
        starttime = dateutil.parser.parse(args.starttime) 
        endtime = dateutil.parser.parse(args.endtime)
    elif args.starttime:
        # 24 hours from start time.
        starttime = dateutil.parser.parse(args.starttime) 
        endtime = starttime + timedelta(days=1)
    elif args.endtime:
        # Prior 24 hours before end time.
        endtime = dateutil.parser.parse(args.endtime) 
        starttime = endtime - timedelta(days=1)
    else:
        # Most recent 24 hours.
        endtime = datetime.utcnow() 
        starttime = endtime - timedelta(days=1)
        start_doy = starttime.timetuple().tm_yday
        end_doy = endtime.timetuple().tm_yday

    print('Start time:', starttime)
    print('End time:  ', endtime)

    if args.iris:
        # Get the data from IRIS.
        net, station, loc, chan = args.channel.split('.')
        print('Attempting to retrieve {}.{}.{}.{} from IRIS...'.format(net, station, loc, chan))
        st = GetIrisDataRange(net, station, loc, chan, starttime, endtime)
        # Write data to a local file.
        st.write('{}.{}.{}.{}.copy.mseed'.format(net, station, loc, chan))
    elif args.server:
        print('Use Seedlink server:', args.server)
        net, station, loc, chan = args.channel.split('.')
        print('Attempting to retrieve {}.{}.{}.{}...'.format(net, station, loc, chan))
        server, port = args.server.split(':')
        client = SeedlinkClient(server, int(port))
        st = client.get_waveforms(net, station, loc, chan, UTCDateTime(starttime), UTCDateTime(endtime))
        # Write data to a local file
        st.write('{}.{}.{}.{}.copy.mseed'.format(net, station, loc, chan))
    else:
        st = Stream()
        t = starttime
        while t < (endtime + timedelta(days=1)):
            year = t.timetuple().tm_year
            doy = t.timetuple().tm_yday

            fname = '{}/{}.{}.{}.mseed'.format(args.path, args.channel, year, doy)
            print('Attempting to open file "{}"...'.format(fname))
            try:
                st += read(fname)
            except Exception as e:
                print(e)
                print('Attempting to continue...')
            t += timedelta(days=1)

# Merge and trim the streams.
st.merge()      # allow gaps
st.trim(starttime=UTCDateTime(starttime), endtime=UTCDateTime(endtime+timedelta(0.1)))
print(st)
if args.verbose:
    print("Data:", st[0].data)

if not st or len(st) == 0 or len(st[0].data) == 0:
       print('No data found.')
       exit(1)

# Read the response file containing the response data for this channel.
inv = read_inventory(args.response_file)
if args.verbose:
    print('inv:', inv[0][0][0].response)

# By default, PPSD plots acceleration. There doesn't seem to be a way to plot
# velocity. 'hydrophone' handling plots the data as velocity but the NLNM/NHNM
# lines are still plotted as acceleration.
plt.rcParams['font.family'] = 'Helvetica'
ppsd = PPSD(
    st[0].stats, 
    metadata=inv, 
    period_step_octaves=1.0/40, 
    ppsd_length=int(args.segment_len),
    overlap=float(args.segment_overlap),
    skip_on_gaps=False)
ppsd.add(st)
fig = ppsd.plot(
    show=False,
    period_lim=(1.0/(st[0].stats.sampling_rate/2), 1.0/0.002))

fig.set_size_inches(10,8)
ax = fig.axes[0]
title = r"$\bf{%s}$" + "\n%s to %s  Acceleration PPSD (%i/%i segments)"
title = title % (ppsd.id,
    ppsd.times_processed[0].date,
    ppsd.times_processed[-1].date,
    ppsd.current_histogram_count,
    len(ppsd.times_processed))
ax.set_title(title)
plt.draw()

if args.show:
    plt.show()

# Before writing the output file, rotate the existing files.
if args.rotate:
    # Rotate the old plots, keeping at most 'args.rotate' number of old copies.
    for i in reversed(range(args.rotate)):
        if i == args.rotate-1:
            try:
                os.remove('{}.{}'.format(args.outfile, i))
            except Exception as e:
                print(e)
        elif i == 0:
            try:
                os.rename(args.outfile, '{}.{}'.format(args.outfile, i+1))
            except Exception as e:
                print(e)
        else:
            try:
                os.rename('{}.{}'.format(args.outfile, i),
                          '{}.{}'.format(args.outfile, i+1))
            except Exception as e:
                print(e)

print('Writing output file:', args.outfile)
plt.savefig(args.outfile, dpi=int(args.dpi), bbox_inches='tight')
plt.close()
exit(0)
