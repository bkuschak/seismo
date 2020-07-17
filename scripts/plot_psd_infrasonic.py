# Plot PSD of the scaled pressure data, derived from the measured capacitance.
#
# 7/6/2020 bkuschak@yahoo.com

import numpy as np
import scipy as sy
import scipy.fftpack as syfp
import pylab as pyl
import matplotlib.pylab as plt
import matplotlib.mlab as mlb
from matplotlib.offsetbox import AnchoredText

# Sample rate.
fs = 90.9       # sps

# Scale factor to convert from data units to Pascal.
# Input data is in pF (4.096 pF per 2^23 counts)
# Calibration factor is 3853 CDC counts/microbar, or 38530 counts/pascal.
units = (1<<23) / 4.096 / 38527 

# Read in data from file here.
# Two columns, timestamp(float), data(float)
# data is differential capacitance in pF

# Real data.
data = np.loadtxt("data7.log.cap",delimiter=" ") 
ch_data = data[:,1]

# Both ports open to atmosphere for noise measurement.
noise = np.loadtxt("data9.log.cap",delimiter=" ") 
ch_noise = noise[:,1]

# Dummy data for testing script.
# ch_data = np.array([1.0, 1.0, 2.0, 3.0])
# ch_noise = np.array([1.0, 1.0, 2.0, 3.0])

# Infrasonic PSD IDC2010_LI low noise model. Estimated from published plots:
# https://link.springer.com/article/10.1007/s00024-012-0573-6
# Base10 logarithm relative to (1 Pa)^2/Hz
idc2010_li = [
        (0.012, -2.1),
        (0.02, -2.7),
        (0.03, -3.2),
        (0.04, -3.55),
        (0.05, -3.75),
        (0.06, -3.95),
        (0.07, -4.05),
        (0.08, -4.15),
        (0.09, -4.25),
        (0.1, -4.45),
        (0.13, -4.25),
        (0.2, -4.2),
        (0.3, -5.0),
        (0.4, -5.4),
        (0.5, -5.6),
        (0.6, -5.7),
        (0.7, -5.8),
        (0.8, -6.05),
        (0.9, -6.3),
        (1.0, -6.5),
        (2.0, -7.75),
        (3.0, -8.5),
        (3.8, -8.85),
        (4.0, -8.9),
        (5.0, -9.1),
        (6.0, -9.25),
        (7.0, -9.4),
        (7.3, -9.45),
        (8.0, -9.75),
        (9.0, -9.90)
]

# Infrasonic PSD IDC2010_HI high noise model. Estimated from published plots:
# https://link.springer.com/article/10.1007/s00024-012-0573-6
# Base10 logarithm relative to (1 Pa)^2/Hz
idc2010_hi = [
        (0.012, 3.6),
        (0.022, 3.45),
        (0.04, 3.05),
        (0.05, 2.9),
        (0.06, 2.5),
        (0.07, 2.25),
        (0.08, 2.1),
        (0.09, 2.06),
        (0.1, 2.0),
        (0.2, 1.5),
        (0.3, 1.2),
        (0.4, 0.8),
        (0.5, 0.45),
        (0.6, 0.05),
        (0.7, -0.05),
        (0.8, -0.3),
        (0.9, -0.55),
        (1.0, -0.8),
        (2.0, -1.3),
        (3.0, -1.6),
        (4.0, -1.85),
        (5.0, -1.95),
        (6.0, -2.05),
        (7.0, -2.2),
        (8.0, -2.3),
        (9.0, -2.5)
]

# Transpose for plotting.
idc2010_li_x,idc2010_li_y = np.array(idc2010_li).T
idc2010_hi_x,idc2010_hi_y = np.array(idc2010_hi).T

# Convert to dB.
idc2010_li_y = 10 * idc2010_li_y
idc2010_hi_y = 10 * idc2010_hi_y

# Scale capacitance to Pascals.
ch_data = ch_data * units
ch_noise = ch_noise * units

# Get the PSD in Pa^2/Hz.
psd_data, f_data = plt.mlab.psd(ch_data, Fs=fs, detrend=mlb.detrend_mean, NFFT=32768)
psd_noise, f_noise = plt.mlab.psd(ch_noise, Fs=fs, detrend=mlb.detrend_mean, NFFT=32768)

# Noise in Pa^2/Hz at 1Hz.
noise_1hz = psd_noise[np.argmax(f_noise >= 1.0)] 

# Bandlimited noise 0.5 Hz to 2.0 Hz.
# Bandlimited noise 0.1 Hz to 50.0 Hz.
# Integrate bandlimited PSD to get noise power.
noise_nb = np.sum([psd*1.0/fs for psd,f in zip(psd_noise,f_noise) if f >= 0.5 and f <= 2.0])
noise_wb = np.sum([psd*1.0/fs for psd,f in zip(psd_noise,f_noise) if f >= 0.1 and f <= 50.0])

# Convert noise power to noise pressure (Pa^2 to Pa).
noise_nb = np.sqrt(noise_nb)
noise_wb = np.sqrt(noise_wb)

# Convert to dB log scale.
psd_data = 10 * np.log10(psd_data)
psd_noise = 10 * np.log10(psd_noise)
noise_1hz_db = 10 * np.log10(noise_1hz)

# Plot the combined PSD.
plt.rc('text', usetex=True)     # use LaTex
fig = plt.figure()
plt.plot(f_data, psd_data, label='Sensor output')
plt.plot(f_noise, psd_noise, label='Sensor noise (both ports open)')
plt.plot(idc2010_hi_x, idc2010_hi_y, linewidth=2, label='IDC2010-HI High Noise Model')
plt.plot(idc2010_li_x, idc2010_li_y, linewidth=2, label='IDC2010-LI Low Noise Model')
plt.xlim(0.01,50)		# Hz
plt.xscale('log')
title = 'AM.BKSVL.01.BDF' 
subtitle = 'Microbarometer Power Spectral Density. 24 hours @ %.1f SPS. AD7746 CAPCHOP=0.' % (fs)
titlestr = r'\begin{center}{\textbf{%s\\}}%s\end{center}' % (title, subtitle)
plt.title(titlestr)
plt.xlabel('Frequency (Hz)')
plt.ylabel('dB Pa\u00b2/Hz')
plt.axes().xaxis.grid(True, which='both')
plt.axes().yaxis.grid(True)
plt.legend()
at = AnchoredText(
    'RMS noise @ 1 Hz: %.2f \u00b5Pa\u00b2/Hz (%.1f dB Pa\u00b2/Hz)\n' \
    'Bandlimited RMS noise 0.5 - 2 Hz: %.1f milliPascal\n' \
    'Bandlimited RMS noise 0.1 - 50 Hz: %.1f milliPascal' \
        % (noise_1hz*1e6, noise_1hz_db, noise_nb*1e3, noise_wb*1e3),
    frameon=True, loc='lower left')
at.patch.set_ec('lightgrey')
at.patch.set_alpha(0.75)
plt.gca().add_artist(at)
plt.show()

