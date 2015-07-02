#                    CONFIGURATION FILE FOR WS2EW
#                    -----------------------------
ModuleId         MOD_EW2WS_A    # Module id of this instance of Ew2Ws
InRing           MUX_DATA_RING  # Transport ring to read multiplexed data waveforms from
Host		 0.0.0.0	# Host name or IP address of the system running WinSDR
Port             4022           # Port number to use when listening or connecting to WinSDR
HeartbeatInt     15             # Heartbeat interval in seconds
#
#                        OPTION PARAMETERS
SocketTimeout	20		# Socket timeout in seconds (default = 60)
RestartWaitTime 20		# Seconds to wait between reconnects (default = 60)
NoDataWaitTime  20              # Seconds to wait before resetting connection
SendAck		15		# number of received packets before sending ACK packet, 0 = don't send ACK packet
Debug		0		# Set to 1 for debug info
#
ConsoleDisplay  0
ControlCExit    0
RefreshTime     0
CheckStdin	0
#
#               SCNL VALUES FOR EACH CHANNEL
#
# This should match the Chan lines in your PsnAdSend.d file
#
#     Stat  Comp Net Loc Bits Gain
#     ----- ---- --- --- ---- ----
Chan  LCGPZ  SHZ  PN  01   21   4
Chan  LCGPE  SHE  PN  02   21   4
Chan  LCGPN  SHN  PN  03   21   4
