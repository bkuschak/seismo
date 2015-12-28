# Plot PSD of the YUMA outputs
# Brian Kuschak <bkuschak@yahoo.com> 4/3/2015
#
import numpy as np
import scipy as sy
import scipy.fftpack as syfp
import pylab as pyl
import matplotlib.pylab as plt
import matplotlib.mlab as mlb

# Read in data from file here
# two columns, time, data.
# generated using Larry's drf2txt_v11: drf2txt.exe -t -c LOW -n 0402_0400 480

#ch_low = np.loadtxt("040315_000000.low.txt") #unfiltered
data_low = np.loadtxt("040215_040000.low.txt",delimiter=",") #unfiltered
ch_low = data_low[:,1]	# 2nd column is ADC samples

# PSD of the USGS New low noise model 
# dB relative to (1 m/s)^2/Hz
# from
# http://gfzpublic.gfz-potsdam.de/pubman/item/escidoc:4017:4/component/escidoc:4018/Chapter_4_rev1.pdf
# period, velocity noise
nlnm =  [(0.1, -203.9),
	 (0.17, -198.1),
	 (0.4, -190.6),
	 (0.8, -187.1),
	 (1.24, -177.8),
	 (2.40, -157.0),
	 (4.3, -144.4),
	 (5.0, -143.1),
	 (6.0, -149.4),
	 (10.0, -159.7),
	 (12.0, -160.6),
	 (15.6, -154.2),
	 (21.9, -166.7),
	 (31.6, -171.0),
	 (45.0, -170.4),
	 (70.0, -166.6),
	 (101.0, -160.9),
	 (154.0, -157.2),
	 (328.0, -153.1),
	 (600.0, -144.8),
	 (10000, -87.9),
	 (100000, -19.1)]

# PSD of the USGS New high noise model 
# dB relative to (1 m/s)^2/Hz
# from
# http://gfzpublic.gfz-potsdam.de/pubman/item/escidoc:4017:4/component/escidoc:4018/Chapter_4_rev1.pdf
# period, velocity noise
nhnm =  [(0.1, -127.5),
	 (0.22, -126.5),
	 (0.32, -136.4),
	 (0.80, -137.9),
	 (3.80, -102.4),
	 (4.60, -99.2),
	 (6.3, -101.0),
	 (7.9, -111.5),
	 (15.4, -112.2),
	 (20.0, -128.4),
	 (354.8, -91.0),
	 (10000, -16.1),
	 (100000, 35.5)]


# transpose ch_low for plotting
nlnm_x,nlnm_y = np.array(nlnm).T
nhnm_x,nhnm_y = np.array(nhnm).T

# convert to frequency domain
nlnm_x = 1.0/nlnm_x
nhnm_x = 1.0/nhnm_x

# Create time data for x axis based on ch_low length
fs = 30.0
x = sy.linspace(1/fs, len(ch_low)/fs, num=len(ch_low))

# scale Yuma output to (m/s)^2/Hz
ch_low = ch_low * 1.87e-9	# 1.87nm/s/count

#plt.psd(ch_low, Fs=fs, detrend=mlb.detrend_mean, NFFT=256*1024, label='Yuma LOW') 
plt.psd(ch_low, Fs=fs, detrend=mlb.detrend_mean, NFFT=32*1024, label='Yuma LOW') 
plt.plot(nlnm_x, nlnm_y, label='NLNM')
plt.plot(nhnm_x, nhnm_y, label='NHNM')

plt.ylim(-200,-50)
plt.xlim(0.001,10)		# Hz
plt.xscale('log')
plt.title('Ground velocity power spectral density. NLNM and NHNM')
plt.xlabel('Frequency (Hz)')
plt.ylabel('dB (m/s)^2/Hz')
#fixme - missing ytick labels
#a=axes.get_xticks().tolist()
#a[1]='change'
#axes.set_yticklabels(a)
#plt.yticks(np.arange(-200,-50, -10))
plt.axes().xaxis.grid(True, which='minor')
plt.axes().yaxis.grid(True)
plt.legend()
plt.show()


