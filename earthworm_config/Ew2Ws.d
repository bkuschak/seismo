#                    CONFIGURATION FILE FOR WS2EW
#                    -----------------------------
ModuleId         MOD_EW2WS_A    # Module id of this instance of Ws2Ew
InRing           MUX_DATA_RING  # Transport ring to read multiplexed data waveforms from
Host		 0.0.0.0	# Host name or IP address of the system running WinSDR
Port             4022           # Port number to use when listening or connecting to WinSDR
HeartbeatInt     10             # Heartbeat interval in seconds
#
#                        OPTION PARAMETERS
#SocketTimeout	20		# Socket timeout in seconds (default = 60)
#RestartWaitTime 20		# Seconds to wait between reconnects (default = 60)
#NoDataWaitTime  20              # Seconds to wait before resetting connection
#SendAck		15		# number of received packets before sending ACK packet, 0 = don't send ACK packet
Debug		2		# Set to 1 for debug info
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
#     Stat  Comp Net Loc Bits Gain
#     ----- ---- --- --- ---- ----
#Chan  CH1   CF1   PN  01   24   2
#Chan  CH2   BHZ  PN  02   24   2
#Chan  CH3   HI1   PN  03   24   2
#Chan  CH4   TMP  PN  04   24   1

Chan  BKFBC  CNF   PN  01   24   2  
Chan  BKFBV  LHZ   PN  02   24   2  
Chan  BKFBB  BHZ   PN  03   24   2 
Chan  BKFBT  TMP   PN  04   24   1 


