#!/usr/bin/env python
#
# Plot a seismic strip chart, typically for 24 hours of data.
# Also dump the data to a WAV file, so you can listen to it.
# Uses text data input, with delimiters, with time and data point on each line
#
# You can get this from WinSDR using drf2txt (v11 or later):
#    drf2txt -t -c LOW -n 0425_0000 720
#
# Then run this script, for example: 
#    python plot_chart.py -x 1024 -y 768  --fs 200 --starttime "4/25/15 00:00 UTC"
#        --hp 0.01 --lp 0.07 --decimate 100 --scale 40e-6 --station "Sunnyvale, CA" 
#        --chan "BHZ Yuma2" -c "M7.8 - 34km ESE of Lamjung, Nepal 06:11:26 UTC" 
#        --fontsize 10 042515_000000.txt
#
# Or for a list of options:
#    python plot_chart.py -h
#
# Output files are chart.png and output.wav, by default
#
# B. Kuschak <bkuschak@yahoo.com> 4/28/15 
#

import numpy as np
import matplotlib.pylab as plt
import matplotlib.mlab as mlb
import scipy.signal as signal
import scipy.io.wavfile as wavfile
import argparse
import sys
import dateutil
import math


# Plot frequency and phase response
def mfreqz(b,a=1):
	w,h = signal.freqz(b,a)
	h_dB = 20 * np.log10 (abs(h))
	plt.subplot(211)
	plt.plot(w/max(w),h_dB)
	plt.ylim(-150, 5)
	plt.ylabel('Magnitude (db)')
	plt.xlabel(r'Normalized Frequency (x$\pi$rad/sample)')
	plt.title(r'Frequency response')
	plt.subplot(212)
	h_Phase = np.unwrap(np.arctan2(np.imag(h),np.real(h)))
	plt.plot(w/max(w),h_Phase)
	plt.ylabel('Phase (radians)')
	plt.xlabel(r'Normalized Frequency (x$\pi$rad/sample)')
	plt.title(r'Phase response')
	plt.subplots_adjust(hspace=0.5)

# FIR linear phase filter
# fixme - use a polyphase filter bank to decimate and filter
def filter_fir(data, order, fs):
	n = order
	a = np.zeros(n)
	b = np.zeros(n)
	# Lowpass filter
	if args.lowpass:
		a = signal.firwin(n, cutoff = args.lowpass/(fs/2), window = 'blackmanharris')
	# Highpass filter with spectral inversion
	if args.highpass:
		b = - signal.firwin(n, cutoff = args.highpass/(fs/2), window = 'blackmanharris'); 
		b[n/2] = b[n/2] + 1
	# Combine into a bandpass filter
	d = - (a+b); d[n/2] = d[n/2] + 1
	if args.response:
		mfreqz(d)
		plt.show()
	output_signal = signal.filtfilt(d, 1, data)	# applied forwards/backwards, linear phase, no lag
	return output_signal

# FIR linear phase decimation filter
def decimate(t, data, factor, order):
	data = signal.decimate(data, factor, n=order, ftype='fir')
	t = t[::factor]
	return t, data

def decimate_nodelay(t, data, factor, order):
	n = order
	#Lowpass filter
	b = signal.firwin(n, cutoff = 0.9/factor, window = 'blackmanharris')
	if args.response:
		mfreqz(b)
		plt.show()
	output_signal = signal.filtfilt(b, 1, data)	# apply forward and backwards, zero phase shift
	output_signal = output_signal[::factor]		# decimate
	t = t[0::factor]
	return t, output_signal

def nice_units(num):
	if num >= 1e-12 and num < 1e-9:
		return ('p', 1e-12)
	if num >= 1e-9 and num < 1e-6:
		return ('n', 1e-9)
	if num >= 1e-6 and num < 1e-3:
		return ('u', 1e-6)
	if num >= 1e-3 and num < 1:
		return ('m', 1e-3)
	return ('unknown', 1)

# Defaults - cmd line can override these
width = 900
height = 1000
dpi = 100
fontsize = 12
scale = 20e-6		# m/s per line, plot scale
units = 1.88e-9		# input data scale
fs = 200.0		# sample rate 
decimation = 100	# factor 
decimation_order = 50	# decimating FIR filter order
bandpass_order = 1001	# bandpass FIR filter order
delimiter = ","		# default delimiter in datafile
response = False	# don't plot filter response by default
outfile = 'chart.png'
chan='BHZ'
station='PSN Station'
date='Unknown'
desc=	'Generate 24-hour plot of seismic activity\n\r' \
	'Example: python %s -x 640 -y 480 --fs 200 --lowpass 0.07\n' \
	'              --highpass 0.01 --chan "BHZ" --station "ABC" 040115_0000.txt' % \
	(sys.argv[0])

# parse command line arguments
parser = argparse.ArgumentParser(description=desc, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('filename', help='filename for the data file')
parser.add_argument('-x', '--width', type=int, default=width, help='width of plot in pixels')
parser.add_argument('-y', '--height', type=int, default=height, help='height of plot in pixels')
parser.add_argument('--fontsize', default=fontsize, help='fontsize (default: 12)')		
parser.add_argument('-n', '--hours', type=int, help='number of hours to plot (default is entire file)')
parser.add_argument('-o', '--out', dest='outfile', default=outfile, 
	help='output filename (default is chart.png)')
parser.add_argument('--units', default=units, type=float, help='input scale (default 1.88e-9)')
parser.add_argument('--dpi', type=int, default=dpi, help='pixels per inch (100 default)')
parser.add_argument('--delimiter', default=delimiter, help='delimiter in the data file. default is ","')
parser.add_argument('--scale', default=scale, type=float, help='scale in units (m/s) per line')
parser.add_argument('--autoscale', action='store_true', help='autoscale based on peak, overrides --scale')
parser.add_argument('--fs', default=fs, required=True, help='sample rate of the data')
parser.add_argument('--decimate', default=decimation, type=int, 
	help='integer factor to decimate by')
parser.add_argument('--decimation_order', default=decimation_order, type=int, 
	help='filter order for the decimation filter')
parser.add_argument('--lp', '--lowpass', dest='lowpass', type=float, help='lowpass cutoff in Hz')
parser.add_argument('--hp', '--highpass', dest='highpass', type=float, help='highpass cutoff in Hz')
parser.add_argument('--bandpass_order', default=bandpass_order, type=int,
	help='filter order for the low/high/bandpass filter (default %d)' % (bandpass_order))
parser.add_argument('--chan', default=chan, help='name of the channel to be printed')
parser.add_argument('--station', default=station, help='name of the station to be printed')
parser.add_argument('--response', default=response, action='store_true', help='plot filter responses')
parser.add_argument('-v', '--verbose', action='count', help='increase verbosity')
parser.add_argument('--starttime', dest='starttime', default=date, 
	help='start time of the data. Ex: 4/25/15 00:00 UTC')
parser.add_argument('-c', '--comment', help='Add a comment to the title')
args = parser.parse_args()

starttime = dateutil.parser.parse(args.starttime) # nice little utility, recognizes time strings

if args.verbose:
	print(args)
	print starttime

# Read in data from file here
# two columns, time, data.
# generated using Larry's drf2txt_v11, example: drf2txt.exe -t -c LOW -n 0402_0400 480
print('Loading data...') 
t, data = np.loadtxt(args.filename, delimiter=args.delimiter, unpack=True) 	

# filter / decimate first. Otherwise, it's hard to get a good cutoff with the FIR filter later
if args.decimate != None:
	print('Decimating by %d...' % (args.decimate)) 
	t, data = decimate_nodelay(t, data, args.decimate, decimation_order)	 
	fs = fs/args.decimate

# scale data from ADC counts to real units, in m/sec
print('Scaling...') 
data =  data * args.units

# filter here...
if args.lowpass != None or args.highpass != None:
	print('Applying filter...') 
	data = filter_fir(data, bandpass_order, fs)

# scale time to minutes
t = t / 60

# find location of maximum magnitude
index_min=data.argmin()
index_max=data.argmax()
data_min=data.min()
data_max=data.max()
if abs(data_min) > abs(data_max):
	data_max = abs(data_min)
	index_max = index_min
time_max = index_max / fs		# in seconds
hour_max = time_max / 3600		
min_max = (time_max % 3600) / 60
sec_max = (min_max - int(min_max)) * 60
print 'Length of data: %d lines, %.2f seconds' % (len(t), t[len(t)-1]-t[0])
#print 'maximum %.3f at %.2f seconds' % (data_max, time_max)
units, factor = nice_units(data_max)

# attempt to autoscale to a reasonable scale
if args.autoscale:
	scale = data_max / 2.5		# peak excursion is 2.5 lines high
else:
	scale = args.scale

# Plot
# Divide the input data up hourly, for N hours, adjusting each X axis 0-60 minutes
# Total Y axis = data_scale_per_line * N+1
# Add scale_per_line to each hour's data, plot
# Add custom Y-axis labels, the UTC time for each line
# Add custom X-axis labels, 0 to 60 minutes
# Add vertical grid evey 10 minutes
print('Plotting...')
plt.rcParams['font.size'] = args.fontsize 	# global font size
fig = plt.figure(figsize=(args.width / args.dpi, args.height / args.dpi), dpi=args.dpi)
fig.set_tight_layout(True)
plt.xlim((0,60))
plt.grid(axis='x')
plt.xlabel('Time (min)')
plt.ylabel('UTC hour')

str = ''
if args.station != None:
	str += '%s ' % (args.station)
if args.chan != None:
	str += '%s ' % (args.chan)
str += '\n'
if args.starttime != None:
	str += 'Start Date: %s ' % (starttime.strftime('%x'))

if args.highpass != None:
	str += 'HP=%.3f Hz ' % (args.highpass)
if args.lowpass != None:
	str += 'LP=%.3f Hz ' % (args.lowpass)

units, factor = nice_units(data_max)
str += '%.0f %sm/s/line\n' % (scale/factor, units)
str += 'Maximum velocity: %.2f %sm/s at %02u:%02u:%02u' % (data_max/factor, units, hour_max, min_max, sec_max)
if args.comment != None:
	str += '\n%s' % (args.comment)
plt.title(str, fontsize=args.fontsize)

# divide data into hourly blocks, for 24 hours
# lines grow downward
yticks = list()
ytickspos = list()

# Plot entire file, or specified number of hours
if args.hours != None:
	hours = args.hours
else:
	hours = int(math.ceil(len(t)/fs/3600))	# round up 

for i in range(0, hours):			
	hourly_t = t[i*3600*fs:(i+1)*3600*fs]
	hourly_data = data[i*3600*fs:(i+1)*3600*fs]
	max_i = i
	hour = (starttime.hour+i) % 24

	# add a UTC time tick for this line
	yticks.append('%d:00' % (hour))
	ytickspos.append(-i*scale);	

	# Only plot if there is data
	if(len(hourly_data) != 0):
		# start each hourly line at zero time
		hourly_t -= hourly_t[0]

		# offset the data to appear on the correct line
		hourly_data = hourly_data - i*scale

		plt.plot(hourly_t, hourly_data, linewidth=0.1, antialiased=False)
		#plt.plot(hourly_t, hourly_data, linewidth=0.1, antialiased=True)

# add labels to plot
plt.yticks(ytickspos, yticks)
	
# Allow a little space above and below
plt.ylim((-(i+1)*scale, scale))

# Save plot as file
fig.savefig(args.outfile, dpi=dpi)

# save file as WAV so we can listen to it
wavfile.write('output.wav', 8000, 0.95*data/data_max)	# 0.95 is largest amplitude

