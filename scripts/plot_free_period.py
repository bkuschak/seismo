# Using the oscilloscope data for free period measurement, calculate the free
# period and the damping ratio. Generate plots.
#
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pylab as plt
import matplotlib.mlab as mlb

class free_period():
    def __init__(self, filename, unit_name):
        # Read data from a CVS file recorded by the MSOX3054A scope.
        self.unit_name = unit_name
        self.plot_filename = filename.replace('.csv', '.png')
        self.data = np.loadtxt(filename, delimiter=',', skiprows=2)
        self.t = self.data[:,0]  # 1st column is time
        self.y = self.data[:,1]  # 2nd column is ADC samples
        self.fs = 1/ (self.t[1] - self.t[0])
        print('Filename:', filename)
        print('  Time duration:', self.t[-1] - self.t[0])
        print('  Sample rate:', self.fs)

    def trim(self, earliest_time, latest_time):
        # Trim the data.
        # Data at the start of the capture may be clipped. Remove it.
        # Data at the end may start drifting. 
        self.earliest = earliest_time
        self.latest = latest_time
        trimmed = [(tp,yp) for (tp,yp) in zip(self.t,self.y) if tp >= earliest_time and tp <= latest_time]
        self.t, self.y = list(zip(*trimmed))
        self.t = np.array(self.t)
        self.y = np.array(self.y)

    def damped_harmonic_oscillator(self, t, amplitude, decay_rate, f, phi, offset):
        return amplitude * np.exp(-decay_rate*t) * np.sin(2*np.pi*f*t + phi) + offset

    def curve_fit(self):
        #popt, pcov = curve_fit(self.damped_harmonic_oscillator, self.t, self.y)
        popt, pcov = curve_fit(self.damped_harmonic_oscillator, self.t, self.y, method='lm')
        self.y_fit = self.damped_harmonic_oscillator(self.t, *popt)
        decay_rate = popt[1]
        freq = np.abs(popt[2])
        omega = 2*np.pi*freq
        self.period = 1.0/freq
        self.zeta = decay_rate / np.sqrt(decay_rate**decay_rate * omega**omega)
        print('period, zeta:', self.period, self.zeta)

    def plot(self, plot_filename=''):
        if plot_filename == '':
            plot_filename = self.plot_filename
        fig, ax1 = plt.subplots()
        ax1.set_ylabel('POS_ERR (volts)')
        ax1.set_xlabel('Time (sec)')
        line1, = ax1.plot(self.t, self.y, 'r-', label='Position')
        line2, = ax1.plot(self.t, self.y_fit, 'b--', label='Curve Fit')
        plt.legend((line1, line2), ('Measured', 'Fit'), loc='upper right')
        plt.title('%s\nFree Period %.2f sec. Damping ratio zeta = %.02f' % (self.unit_name, self.period, self.zeta))
        if plot_filename:
            plt.savefig(plot_filename)
        plt.show()

# Yuma #1
p = free_period('free_period_yuma1.csv', 'Yuma #1')
p.curve_fit()
p.plot()

# Yuma #3
p = free_period('free_period_yuma3.csv', 'Yuma #3')
p.trim(0.85, 6.85)
p.curve_fit()
p.plot()
