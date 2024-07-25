# Plot probabilistic PSD of velocity using a miniseed input file.

import argparse
from datetime import datetime, timedelta
import dateutil
import matplotlib.pylab as plt
import matplotlib.mlab as mlb
import numpy as np
from obspy import read, read_inventory, Stream, UTCDateTime
from obspy.io.xseed import Parser
from obspy.signal import PPSD
import pylab as pyl
import scipy as sy
import scipy.fftpack as syfp
import sys

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
        endtime = datetime.now() 
        starttime = endtime - timedelta(days=1)
        start_doy = starttime.timetuple().tm_yday
        end_doy = endtime.timetuple().tm_yday

    print('Start time:', starttime)
    print('End time:  ', endtime)

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
st.trim(starttime=UTCDateTime(starttime), endtime=UTCDateTime(endtime))
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

# By default, PPSD plots acceleration. To plot velocity, use 'hydrophone' method.
plt.rcParams['font.family'] = 'Helvetica'
ppsd = PPSD(
    st[0].stats, 
    metadata=inv, 
    period_step_octaves=1.0/40, 
    ppsd_length=int(args.segment_len),
    overlap=float(args.segment_overlap),
    skip_on_gaps=True,
    special_handling='hydrophone') # no differentiation after instrument correction
ppsd.add(st)
fig = ppsd.plot(
    show=False, 
    xaxis_frequency=True,
    period_lim=(0.005, st[0].stats.sampling_rate/2))

fig.set_size_inches(10,8)
ax = fig.axes[0]
ax.set_ylabel('Amplitude [$m^2/s^2/Hz$] [dB]')
title = r"$\bf{%s}$" + "\n%s to %s  Velocity PPSD (%i/%i segments)"
title = title % (ppsd.id,
    ppsd.times_processed[0].date,
    ppsd.times_processed[-1].date,
    ppsd.current_histogram_count,
    len(ppsd.times_processed))
ax.set_title(title)
plt.draw()

if args.show:
    plt.show()

print('Writing output file:', outfile)
plt.savefig(args.outfile, dpi=int(args.dpi), bbox_inches='tight')
plt.close()
exit(0)
