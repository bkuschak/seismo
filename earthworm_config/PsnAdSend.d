#                    CONFIGURATION FILE FOR PSNADSEND VERSION 2.x
#                    --------------------------------------------
#
ModuleId           MOD_PSNADSEND_A	# Module id of this instance of PsnAdSend
OutRing            WAVE_RING      	# Transport ring to write waveforms to
MuxDataRing	   MUX_DATA_RING	# Used to send raw A/D data to a ring. Comment out or set to 0 if not used

Debug              1                    # Currently enables time reference debugging

# For Windows use port number
#CommPortTcpHost    1              	# Comm Port Number for Windows
#
# For Linux use port device string 
CommPortTcpHost   /dev/ttyUSB0         # Comm Port String for Linux
#
# For TCP/IP Connection to device use IP address or host string 
#CommPortTcpHost   192.168.1.24         # This is the same for Linux and Windows
TcpPort		   8011			# TCP Port Number to use when connecting to the RS-232 host adapter
#
TcpMode		   0			# Set to 1 for TCP/IP connection to host server
#
#
PortSpeed          38400          	# Comm Port Baud Rate
HeartbeatInt       5             	# Heartbeat interval in seconds
#
ConsoleDisplay     0                    # Windows Only; if 1 use console functions to redisplay status
ControlCExit       0	                # If 1 exit on sigint control-c event
RefreshTime        10	                # Auto Status Display Refresh Time, 0 = no status display
CheckStdin         0                    # Windows Only; if 1 check for user input
#
#                        ADC CONFIGURATION
ChanRate           200            	# Sampling rate in samples/second
AdcDataSize        4                    # ADC Data trace buffer size. Can be 2 or 4 bytes
#
#                         TIME INFORMATION
NoDataTimeout      30			# No Data Timeout in seconds
TimeOffset         0              	# Time Reference offset in milliseconds
UpdateSysClock     1              	# 1 = PC time updated with AD board time
HighToLowPPS       0              	# 1 = PPS Signal direction is High to Low
NoPPSLedStatus     1			# 1 = Disable 1PPS LED blinking
LogMessages        1              	# 1 = Log messages from DLL & ADC to log file
NoSendBadTime      0			# 1 = Only send packets with good GPS lock
ExitOnTimeout	   0			# 1 = Exit if timeout error

# New for PsnAdSend 2.5 and above
SystemTimeError    60			# Send error message to StatMgr if the time difference
					# in seconds. 0 = no time test
# New for PsnAdSend 2.5 and above
PPSTimeError       10			# Send error message to StatMgr if the 1PPS error exceeds this amount
                                        # in milliseconds. 0 = no 1PPS test
# New for PsnAdSend 2.5 and above
NoLockTimeError    30			# Send error message to StatMgr if no reference lock after this amount
                                        # of minutes
# New for PsnAdSend 2.5 and above
FilterSysTimeDiff  1			# 1 = Do not log System to A/D board time difference messages	
FilterGPSMessages  0			# 1 = Do not log good GPSRef: time messages 

#
# Time Reference Types:
# PC = Use PC Time, GARMIN = Garmin GPS 16 or 18, MOT_NMEA = Motorola ONCORE NMEA, 
# MOT_BIN = Motorola ONCORE Binary, WWV = WWV (must have WWV option on the ADC board )
# SKG = Sure Electronics SKG GPS Board
# OEM_4800 or OEM_9600 = Generic receiver running at 4800 or 9600 baud.
#
TimeRefType      GARMIN			# One of the types above	 winsdr crash
#TimeRefType      WWV			# One of the types above	 no crash
#
#TimeFileName     c:\tmp\PsnSendTime	# Path and root name of the time info file
TimeFileName     /tmp/PsnSendTime      # use something like this for Linux
#
# Filter params for Low-Pass and High-Pass Filters; Channel Number, Type, Cutoff Freq, Poles
# Ch# is one of the channel numbers below. This includes any derived channels using the AddChan command
# Type can be one of the following; LP = Low-Pass or HP = High-Pass
# Cutoff is the filter 3 db point in Hz
# Poles is the filter poles. This should be a even number between 2 and 16
#
#       Ch#  Type Cutoff Poles
#       ---  ---- ------ -----
#Filter   1    LP    20     2
#Filter   1    HP    1      2
#
#Filter   2    LP    10     4
#Filter   2    HP    1      4

# Filter params for inverse (period extending) filter;
# Sensor Frequency is in Hz 
# Sensor Q is the Q or damping factor of the sensor
# FilterFreq sets the low end frequency in Hz of the period extending filter
# FilterQ is the Q of the single pole FilterFreq
#
#     Ch#  Type SensorFreq SensorQ FilterFreq FilterQ
#Filter 1   INV      4.5      .707      .1      .707
#

#    SCNL VALUES FOR EACH ADC CHANNEL
#
# The number of Chan directives below will set how many channels to record from the ADC Board
# Stat = Station ID; can be 1 to 5 chars, 
# Comp = Component Name; should be 3 chars, 
# Net  = Network ID; should be 2 chars 
# Loc  = Location; should be 2 chars
# Bits = How many ADC bits to use from the ADC board for this channel
# Gain = ADC channel Gain. Only used by 24 Bit converter boards
# FilterDly = Low-Pass Filter Delay in Milliseconds
# Invert = (Y)es will invert the ADC channel data
# Send = (Y)es will send the channel data to the Earthworm ring
# DcOffset = Adds a DC Offset to the incoming data; Integer number in ADC counts

#
#     Stat  Comp Net Loc Bits Gain FltrDly Invert Send DcOffset
#     ----- ---- --- --- ---- ---- ------- ------ ---- --------
#Chan  CH1   CF1  PN  01   24   2      0      N      Y     0
#Chan  CH2   BHZ  PN  02   24   2      0      N      Y     0
#Chan  CH3   HI1  PN  03   24   2      0      N      Y     0
#Chan  CH4   TMP  PN  04   24   1      0      N      Y     0
Chan  BKFBC  CNF   PN  01   24   2      0      N      Y     0
Chan  BKFBV  LHZ   PN  02   24   2      0      N      Y     0
Chan  BKFBB  BHZ   PN  03   24   2      0      N      Y     0
Chan  BKFBT  TMP   PN  04   24   1      0      N      Y     0

#Example for 4 Channel 24-Bit or Strong Motion Boards
#Chan CH1   BHZ  PN  01   20   32     0      N      Y     0
#Chan CH2   BHN  PN  02   20   32     0      N      Y     0
#Chan CH3   BHE  PN  03   20   32     0      N      Y     0
#Chan CH4   SHE  PN  04   20   8      0      N      Y     0

# The number of AddChan directives below will set how many additional channels to derive from the 
# real ADC channels above
#
#       AdcCh Stat  Comp Net Loc Bits FltrDly Invert Send DcOffset
#       ----- ----- ---- --- --- ---- ------- ------ ---- --------
#AddChan  2    CH9   BHN  PN  01  16      0      N     Y     0
#AddChan  7    CH10  AHE  PN  01  16      0      N     Y     0
#
# end of file
