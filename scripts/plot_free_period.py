# Take the oscilloscope data for free period measurement and determine
# the damping ratio 
#
import numpy as np
import scipy.integrate as int
import matplotlib.pylab as plt
import matplotlib.mlab as mlb


# Read in data from file here
data = np.loadtxt("free_period.txt")
t = data[:,0]  # 1st column is time
pos = data[:,1]  # 2nd column is ADC samples
pos = pos - np.mean(pos) + 0.01	# zero bias plus a little fudge factor
fs = 1/ (t[1] - t[0])

#plt.figure()
#plt.psd(pos, Fs=fs, detrend=mlb.detrend_mean, NFFT=256*1024)
#plt.yscale('linear')

# frequency measured elsewhere
f = 1/2.26

# harmonic oscillator ODE
def dy(y, t, zeta, w0):
	x, p = y[0], y[1]
	dx = p
	dp = -2 * zeta * w0 * p - w0**2 * x
	return [dx, dp]

#initial state
y0 = [pos[0]+0.01, -0.09]	# chosen for best fit
# time coordinate to solve for
w0 = 2*np.pi*f

# solve
zeta = 0.15	# estimate
y1 = int.odeint(dy, y0, t, args=(zeta, w0))

# plot time series
fig, ax1 = plt.subplots()
ax1.set_ylabel('Volts')
line1, = ax1.plot(t, pos, 'r-', label='Position')
line2, = ax1.plot(t, y1[:,0], label='Fit')
plt.legend((line1, line2), ('Free Period', 'Fit'), loc='upper right')
plt.title('Free Period %.2f sec. Damping ratio zeta = %.02f' % (1/f, zeta))
plt.show()

