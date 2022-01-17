#                    CONFIGURATION FILE FOR WS2EW
#                    -----------------------------
ModuleId         MOD_EW2WS_A    # Module id of this instance of Ws2Ew
InRing           MUX_DATA_RING  # Transport ring to read multiplexed data waveforms from
				# Note this ring has NO derived channels, NO Filtering/Offset applied. Only raw samples.
Host		 0.0.0.0	# Host name or IP address of the system running WinSDR
Port             4022           # Port number to use when listening or connecting to WinSDR
HeartbeatInt     10             # Heartbeat interval in seconds
#
#                        OPTION PARAMETERS
#SocketTimeout	20		# Socket timeout in seconds (default = 60)
#RestartWaitTime 20		# Seconds to wait between reconnects (default = 60)
#NoDataWaitTime  20              # Seconds to wait before resetting connection
#SendAck		15		# number of received packets before sending ACK packet, 0 = don't send ACK packet
Debug		0		# Set to >1 for debug info
#
ConsoleDisplay  0
ControlCExit    1
RefreshTime     10
CheckStdin	1
#
#               SCNL VALUES FOR EACH CHANNEL
#
# This should match the Chan lines in your PsnAdSend.d file
#
# CH1: Vertical seismo. Unit 1. Raw CH1. Low gain output.
# CH2: Vertical seismo. Unit 1. Raw CH2. Centering force output.
# CH3: Vertical seismo. Unit 2. Raw CH3. Low gain output.
# CH4: Vertical seismo. Unit 2. Raw CH4. Temperature output.
#
# WinSDR seems to name channels by the Station only, not SCNL, so we need to give fake names here 
# so WinSDR can distinguish the different channels.
#
#     Stat  Comp  Net Loc Bits Gain
#     ----- ----  --- --- ---- ----
Chan  BHZ1    BHZ   PN  01   24   2  
Chan  OEC1    OEC   PN  01   24   1  
Chan  BHZ2    BHZ   PN  02   24   2 
Chan  OKS2    OKS   PN  02   24   1 

