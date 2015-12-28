# Plot PSD of the YUMA outputs.
# Both velocity and acceleration plots.
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
data_low = np.loadtxt("040215_040000.low.txt",delimiter=",") #unfiltered night 30 Hz
#data_low = np.loadtxt("040215_130000.low.txt",delimiter=",") #unfiltered day 30 Hz
# drf2txt  -P "/Volumes/C/Program Files/WinSDR" -R "/Volumes/C/Program Files/WinSDR/data" -c CF -T -n -o adc_noise_ch1_shorted -s 0515_171500 120
#data_low = np.loadtxt("adc_noise_ch1_shorted",delimiter=" ") # unfiltered ADC noise

ch_low = data_low[:,1]	# 2nd column is ADC samples
fs = 30.0

# Read noise data from SPICE simulation
data_noise = np.loadtxt("spice_noise_ad706a.txt")	#AD706A
#data_noise = np.loadtxt("spice_noise.txt")	#LT1112
#data_noise = np.loadtxt("YUMA2 Noise.txt")	#Brett's circuit
inoise_f = data_noise[:,0]
inoise_y = data_noise[:,1]	

# Velocity PSD of the USGS New low noise model 
# dB relative to (1 m/s)^2/Hz
# from
# http://gfzpublic.gfz-potsdam.de/pubman/item/escidoc:4017:4/component/escidoc:4018/Chapter_4_rev1.pdf
# period, velocity noise
nlnm_vel =  [(0.1, -203.9),
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

# Velocity PSD of the USGS New high noise model 
# dB relative to (1 m/s)^2/Hz
# from
# http://gfzpublic.gfz-potsdam.de/pubman/item/escidoc:4017:4/component/escidoc:4018/Chapter_4_rev1.pdf
# period, velocity noise
nhnm_vel =  [(0.1, -127.5),
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

# Acceleration PSD of the USGS New low noise model 
# dB relative to (1 m/s^2)^2/Hz
# from
# http://gfzpublic.gfz-potsdam.de/pubman/item/escidoc:4017:4/component/escidoc:4018/Chapter_4_rev1.pdf
# period, velocity noise
nlnm_accel =  [(0.1, -168.0),
	 (0.17, -166.7),
	 (0.4, -166.7),
	 (0.8, -169.2),
	 (1.24, -163.7),
	 (2.40, -148.6),
	 (4.3, -141.1),
	 (5.0, -141.1),
	 (6.0, -149.0),
	 (10.0, -163.8),
	 (12.0, -166.2),
	 (15.6, -162.1),
	 (21.9, -177.5),
	 (31.6, -185.0),
	 (45.0, -187.5),
	 (70.0, -187.5),
	 (101.0, -185.0),
	 (154.0, -185.0),
	 (328.0, -187.5),
	 (600.0, -184.4),
	 (10000, -151.9),
	 (100000, -103.1)]

# Acceleration PSD of the USGS New high noise model 
# dB relative to (1 m/s^2)^2/Hz
# from
# http://gfzpublic.gfz-potsdam.de/pubman/item/escidoc:4017:4/component/escidoc:4018/Chapter_4_rev1.pdf
# period, velocity noise
nhnm_accel =  [(0.1, -91.5),
	 (0.22, -97.4),
	 (0.32, -110.5),
	 (0.80, -120.0),
	 (3.80, -98.0),
	 (4.60, -96.5),
	 (6.3, -101.0),
	 (7.9, -113.5),
	 (15.4, -120.0),
	 (20.0, -138.5),
	 (354.8, -126.0),
	 (10000, -80.1),
	 (100000, -48.5)]


# transpose for plotting
nlnm_vel_x,nlnm_vel_y = np.array(nlnm_vel).T
nhnm_vel_x,nhnm_vel_y = np.array(nhnm_vel).T
nlnm_accel_x,nlnm_accel_y = np.array(nlnm_accel).T
nhnm_accel_x,nhnm_accel_y = np.array(nhnm_accel).T

# convert table from period to frequency 
nlnm_vel_x = 1.0/nlnm_vel_x
nhnm_vel_x = 1.0/nhnm_vel_x
nlnm_accel_x = 1.0/nlnm_accel_x
nhnm_accel_x = 1.0/nhnm_accel_x

# Create time data for x axis based on ch_low length
x = sy.linspace(1/fs, len(ch_low)/fs, num=len(ch_low))

# scale Yuma output to (m/s)^2/Hz
ch_low = ch_low * 1.87e-9	# 1.87nm/s/count

# get the velocity PSD first
psd_vel, f_vel = plt.mlab.psd(ch_low, Fs=fs, detrend=mlb.detrend_mean, NFFT=32*1024)

# convert velocity to acceleration by multiplying point by point with frequencies
# (multiplication by j omega in freq domain is differentiation, PSD is squared)
psd_accel = psd_vel * pow((2 * np.pi * f_vel), 2)
inoise_accel_y = inoise_y * (2 * np.pi * inoise_f)

# convert to log scale
psd_vel = 10 * np.log10(psd_vel)
psd_accel = 10 * np.log10(psd_accel)
inoise_y = 20 * np.log10(inoise_y)		# voltage noise to power noise 
inoise_accel_y = 20 * np.log10(inoise_accel_y)	# voltage noise to power noise 

# Velocity PSD
plt.figure()
plt.plot(f_vel, psd_vel, label='Yuma2')
plt.plot(nlnm_vel_x, nlnm_vel_y, label='NLNM')
plt.plot(nhnm_vel_x, nhnm_vel_y, label='NHNM')
plt.plot(inoise_f, inoise_y, '--', label='Yuma2 noise floor')
plt.ylim(-200,-50)
plt.xlim(0.001,10)		# Hz
plt.xscale('log')
plt.title('Ground velocity power spectral density. NLNM and NHNM')
plt.xlabel('Frequency (Hz)')
plt.ylabel('dB (m/s)^2/Hz')
plt.axes().xaxis.grid(True, which='minor')
plt.axes().yaxis.grid(True)
plt.legend()
#plt.show()

# Acceleration PSD
plt.figure()
plt.plot(f_vel, psd_accel, label='Yuma2')
plt.plot(nlnm_accel_x, nlnm_accel_y, label='NLNM')
plt.plot(nhnm_accel_x, nhnm_accel_y, label='NHNM')
plt.plot(inoise_f, inoise_accel_y, '--', label='Yuma2 noise floor')
plt.legend()
plt.ylim(-200,-50)
plt.xlim(0.001,10)		# Hz
plt.xscale('log')
plt.title('Ground acceleration power spectral density. NLNM and NHNM')
plt.xlabel('Frequency (Hz)')
plt.ylabel('dB (m/s^2)^2/Hz')
plt.axes().xaxis.grid(True, which='minor')
plt.axes().yaxis.grid(True)
plt.legend()
plt.show()

# old method just used matplotlib's psd plotting function
#plt.figure()
#plt.psd(ch_low, Fs=fs, detrend=mlb.detrend_mean, NFFT=32*1024, label='Yuma LOW') 
#plt.plot(nlnm_vel_x, nlnm_vel_y, label='NLNM')
#plt.plot(nhnm_vel_x, nhnm_vel_y, label='NHNM')
#plt.ylim(-200,-50)
#plt.xlim(0.001,10)		# Hz
#plt.xscale('log')
#plt.title('Ground velocity power spectral density. NLNM and NHNM')
#plt.xlabel('Frequency (Hz)')
#plt.ylabel('dB (m/s)^2/Hz')
#fixme - missing ytick labels
#a=axes.get_xticks().tolist()
#a[1]='change'
#axes.set_yticklabels(a)
#plt.yticks(np.arange(-200,-50, -10))
#plt.axes().xaxis.grid(True, which='minor')
#plt.axes().yaxis.grid(True)
#plt.legend()
#plt.show()


