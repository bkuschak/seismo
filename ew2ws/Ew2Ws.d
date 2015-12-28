#                    CONFIGURATION FILE FOR EW2WS
#                    -----------------------------
ModuleId         MOD_EW2WS_A    # Module id of this instance of Ew2Ws
InRing           MUX_DATA_RING  # Transport ring to read multiplexed data waveforms from
Host		 0.0.0.0	# Local address to listen on. 0.0.0.0 to listen on all interfaces.
Port             4022           # Port number to listen on
HeartbeatInt     15             # Heartbeat interval in seconds
#
#                     OPTION PARAMETERS
Debug		 0		# Set to 1 or higher for debug info
MaxConnections   8              # Maximum concurrent WinSDR clients connected. Higher = more memory. 
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
