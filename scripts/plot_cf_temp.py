# Plot the centering force vs temperature, to estimate the spring temperature coefficient.
#
import numpy as np
import scipy as sy
import scipy.fftpack as syfp
import pylab as pyl
import matplotlib.pylab as plt
import matplotlib.mlab as mlb

# Read in data from file here
data = np.loadtxt("040615_000000.temp.txt",delimiter=",") 
#t = data[:,0]  # 1st column is time
#adc = data[:,1]  # 2nd column is ADC samples
adc_temp = data[:]  # only column is ADC samples
data = np.loadtxt("040615_000000.cf.txt",delimiter=",") 
adc_cf = data[:]  # only column is ADC samples
length = min(len(adc_temp), len(adc_cf))
adc_cf = adc_cf[0:length]
adc_temp = adc_temp[0:length]
x = np.linspace(1, length, length)

# scale
# CF channel is on +/-10V channel with gain=2
# temp is on +/-2.5V channel with gain=1
adc_cf = adc_cf * 17 * 2.5 / 2 / pow(2,23)
adc_temp = adc_temp * 2.5 / pow(2,23) * 100
x = x / 0.2 / 60 / 60 		# hours - decimated to 0.2 SPS

# plot time series
fig, ax1 = plt.subplots()
ax2 = ax1.twinx()
ax1.set_ylabel('Internal Temp (C)')
ax2.set_ylabel('CF (Volts)')
ax1.set_xlabel('hours')
plt.title('CF response vs. temperature')
#plt.plot(t, adc)
line1, = ax1.plot(x, adc_temp, 'r-', label='TEMP')
line2, = ax2.plot(x, -adc_cf, 'b-', label='-CF')
plt.legend((line1, line2), ('TEMP', '-CF'), loc='upper left')

# annotate - we had a data gap which caused discontinuity
ax1.annotate('data gap', xy=(78.125, 29.35),  xycoords='data',
	xytext=(0.4, 0.95), textcoords='axes fraction',
	arrowprops=dict(facecolor='black', shrink=0.05),
	horizontalalignment='right', verticalalignment='top',
	)

plt.show()

# temperature coefficient
coef = np.polyfit(adc_temp, adc_cf, 1)
polynomial = np.poly1d(coef)
xs = np.arange(28,30.2,0.1)
#ys = polynomial(adc_temp)
ys = polynomial(xs)
print coef
print polynomial

#plt.figure()
fig, ax1 = plt.subplots()
plt.title('Centering Force vs Temperature')
ax1.set_xlabel('Internal Temp (C)')
ax1.set_ylabel('CF (Volts)')
plt.title('CF response vs. temperature')
line1, = plt.plot(adc_temp, adc_cf, '.')
#plt.plot(adc_temp, ys)
line2, = plt.plot(xs, ys)
plt.legend((line1, line2), ('CF vs Temp', 'Fit'), loc='upper right')
title = 'CF = %.3f x Temp(C) + %.3f Volts' % (coef[0], coef[1])
ax1.annotate(title, xy=(28.2, 0.782),  xycoords='data',
	xytext=(0.55, 0.25), textcoords='axes fraction',
	arrowprops=dict(facecolor='black', shrink=0.05),
	horizontalalignment='right', verticalalignment='top',
	)
plt.show()
