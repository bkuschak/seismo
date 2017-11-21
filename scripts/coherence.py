#!/usr/bin/python 
#
# Self-noise computation based on coherence function.
# Using data from two colocated Yuma-2 seismometers.
# Plotted in terms of velocity and acceleration.
#
# Adapted from: http://www.earthmode.org/PSD.html
#
# For details on this method, refer to: 
# Holcomb, G. L. A Direct Method for Calculating Instrument Noise Levels in Side-by-side 
# Seismometer Evaluation. USGS Open-File Report 89-214. Albequerue, NM. 1989
#
# B. Kuschak <bkuschak@yahoo.com> 12/29/2015
#

import numpy as np
import scipy as sy
import scipy.fftpack as syfp
import pylab as pyl
import matplotlib.pylab as plt
import matplotlib.mlab as mlab
import matplotlib.ticker as ticker
from matplotlib.ticker import MultipleLocator, FormatStrFormatter

# Some constants
fs = 200.0							# 200 sps
nfft = 256*1024
plt.rcParams['figure.figsize'] = 16, 8

# Load data from each seismometer
# Data is formatted: time, value
# generated using Larry's drf2txt_v11: drf2txt.exe -t -c BK1L -n 1229_0000 240
#
# Separate files
#data_u1 = np.loadtxt("bk1l_122915_000000.txt", delimiter=',')
#t_u1 = data_u1[:,0].astype(int)
#samples_u1 = data_u1[:,1].astype(int)
#
#data_u2 = np.loadtxt("bk2l_122915_000000.txt", delimiter=',')
#t_u2 = data_u2[:,0].astype(int)
#samples_u2 = data_u2[:,1].astype(int)
#

# One file for both
# Data is formatted: time, ch1, ch2, ch3, ch4
data = np.loadtxt("122615_000000.txt", delimiter=',')		# 24 hr low activity 0.002 Hz HP
t_u1 = data[:,0].astype(int)
t_u2 = t_u1
samples_u1 = data[:,2].astype(int)				# CH2
samples_u2 = data[:,1].astype(int)				# CH1

# Equalize the length
l = min(len(samples_u1), len(samples_u2))
print 'Data length is %d seconds.' % (l/fs)
samples_u1 = samples_u1[0:l]
samples_u2 = samples_u2[0:l]

# Remove any DC offset from the signals.  
#samples_u1 = samples_u1 - np.mean(samples_u1)
#samples_u2 = samples_u2 - np.mean(samples_u2)

# Read noise data from SPICE simulation
data_noise = np.loadtxt("spice_noise_ad706a.txt")		# AD706A
inoise_f = data_noise[:,0]
inoise_y = data_noise[:,1]	

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


# transpose for plotting
nlnm_vel_x, nlnm_vel_y = np.array(nlnm_vel).T
nhnm_vel_x, nhnm_vel_y = np.array(nhnm_vel).T
nlnm_accel_x, nlnm_accel_y = np.array(nlnm_accel).T
nhnm_accel_x, nhnm_accel_y = np.array(nhnm_accel).T

# convert table from period to frequency 
nlnm_vel_x = 1.0/nlnm_vel_x
nhnm_vel_x = 1.0/nhnm_vel_x
nlnm_accel_x = 1.0/nlnm_accel_x
nhnm_accel_x = 1.0/nhnm_accel_x

# Create time data for x axis based on samples_u1 length
#x = sy.linspace(1/fs, len(samples_u1)/fs, num=len(samples_u1))

# scale Yuma output to m/s
samples_u1 = samples_u1 * 1.87e-9	# 1.87 nm/s/count
samples_u2 = samples_u2 * 3.14e-9	# 3.14 nm/s/count


#########
# Compute coherence and plot the output.  Do this as a function, so we can run it with both
# velocity and acceleration data.
# (The f_psd, csd here are probably all the same, but just to be safe, treat them separately)
def plot_coherence(str, units, psd_u1, psd_u2, csd, inoise, nlnm, nhnm, f_psd_u1, f_psd_u2, f_csd, f_inoise, f_nlnm, f_nhnm):

	# Compute gamma squared, the coherence function
	# (is this the same for velocity and accel data?)
	gamma_sq = np.absolute(csd)**2 / (psd_u1 * psd_u2)
	gamma = np.sqrt(gamma_sq)

	# Compute phase of CSD
	phase = np.angle(csd, deg=True)
	phase[phase<-90] += 360

	# Compute self noise
	self_noise_u1 = psd_u1 * (1 - gamma)
	self_noise_u2 = psd_u2 * (1 - gamma)

	# convert to log scale
	psd_u1 = 10 * np.log10(psd_u1)
	psd_u2 = 10 * np.log10(psd_u2)
	self_noise_u1 = 10 * np.log10(self_noise_u1)
	self_noise_u2 = 10 * np.log10(self_noise_u2)
	csd = 10 * np.log10(csd)
	inoise = 20 * np.log10(inoise)		# voltage noise to power noise 

	# Neat trick to format x axis with real numbers, not powers of 10
	formatter = ticker.FuncFormatter(lambda y,pos: ('{{:.{:1d}f}}'.format(int(np.maximum(-np.log10(y),0)))).format(y))

	# Plot Coherence
	#plt.figure()
	fig, ax1 = plt.subplots()
	ax2 = ax1.twinx()
	ax2.plot(f_psd_u1, gamma_sq, color='saddlebrown', alpha=0.5);
	ax2.set_ylabel('Coherence (gamma^2)')
	ax2.set_xlabel('Frequency (Hz)')
	ax2.set_xscale('log')
	ax2.xaxis.set_major_formatter(formatter)
	ax2.xaxis.grid(True, which='both')
	ax2.yaxis.grid(False)

	# Plot PSD
	ax1.plot(f_nlnm, nlnm, color='black', linewidth=2, label='NLNM')
	ax1.plot(f_nhnm, nhnm, color='black', linewidth=2, label='NHNM')
	ax1.plot(f_psd_u1, psd_u1, color='gold', alpha=0.5, label='Unit 1')
	ax1.plot(f_psd_u2, psd_u2, color='green', alpha=0.5, label='Unit 2')
	ax1.plot(f_psd_u1, self_noise_u1, color='blue', alpha=0.5, label='Self Noise Unit 1')
	ax1.plot(f_psd_u2, self_noise_u2, color='red', alpha=0.5, label='Self Noise Unit 2')
	ax1.plot(f_inoise, inoise, '--', color='cyan', label='Yuma2 noise floor')
	ax1.set_ylim(-200,-50)
	ax1.set_xlim(0.001,100)
	ax1.set_xscale('log')
	ax1.set_title('Yuma2 %s PSD and Coherence vs. NLNM and NHNM' % (str))
	ax1.set_xlabel('Frequency (Hz)')
	ax1.set_ylabel(units)
	ax1.xaxis.set_major_formatter(formatter)
	ax1.yaxis.set_major_locator(MultipleLocator(10))
	ax1.xaxis.grid(True, which='both')
	ax1.yaxis.grid(True, which='major')
	ax1.plot(1, 1, color='saddlebrown', label='Coherence')	# force onto the legend
	leg = ax1.legend(loc='upper left')
	leg.get_frame().set_alpha(1.0)
	plt.show()

	# Plot coherence and phase separately
	plt.figure()
	plt.subplot(211)
	plt.title('Yuma2 %s Coherence and Phase Between Unit 1 and Unit 2' % (str))
	plt.plot(f_csd, phase, color='blue', label='Phase')
	plt.ylabel('Phase (deg)')
	plt.xscale('log')
	plt.xlim(0.001,100)
	plt.gca().xaxis.set_major_formatter(formatter)
	plt.grid(True, which='both')
	leg = plt.legend(loc='upper left')
	leg.get_frame().set_alpha(1.0)
	plt.subplot(212)
	plt.plot(f_csd, gamma_sq, color='blue', label='Coherence')
	plt.ylabel('Coherence (gamma^2)')
	plt.xlabel('Frequency (Hz)')
	plt.xscale('log')
	plt.xlim(0.001,100)
	plt.gca().xaxis.set_major_formatter(formatter)
	plt.grid(True, which='both')
	leg = plt.legend(loc='upper left')
	leg.get_frame().set_alpha(1.0)
	plt.show()

#########


# calculate the velocity PSDs first
(psd_u1, f_u1) = mlab.psd(samples_u1, Fs=fs, NFFT=nfft)
(psd_u2, f_u2) = mlab.psd(samples_u2, Fs=fs, NFFT=nfft)

# calculate the cross spectral density
(csd, f_csd) = mlab.csd(samples_u1, samples_u2, NFFT=nfft, Fs=fs, sides='default')

plot_coherence(	'Velocity', 'dB m^2/sec^2 / Hz', 
		psd_u1, psd_u2, csd, inoise_y, nlnm_vel_y, nhnm_vel_y, 
		f_u1, f_u2, f_csd, inoise_f, nlnm_vel_x, nhnm_vel_x)

# we want to also display the data in terms of acceleration
# convert velocity to acceleration by multiplying point by point with frequencies
# (multiplication by j omega in freq domain is differentiation, PSD is squared)
psd_u1 = psd_u1 * pow((2 * np.pi * f_u1), 2)
psd_u2 = psd_u2 * pow((2 * np.pi * f_u2), 2)
csd = csd * pow((2 * np.pi * f_csd), 2)
inoise_y = inoise_y * (2 * np.pi * inoise_f)

plot_coherence(	'Acceleration', 'dB m^2/sec^4 / Hz', 
		psd_u1, psd_u2, csd, inoise_y, nlnm_accel_y, nhnm_accel_y, 
		f_u1, f_u2, f_csd, inoise_f, nlnm_accel_x, nhnm_accel_x)


