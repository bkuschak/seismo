#
#  ew2ringserver configuration file
#
#
 MyModuleId     MOD_EW2RINGSERVER   # module id for this program
 RingName       WAVE_RING           # transport ring to use for input
 RSAddress      archive.local:16000 # address of destination ringserver
                                    # in host:port format
 HeartBeatInt   10                  # EW internal heartbeat interval (sec)
 LogFile        0                   # If 0, don't write logfile; if 1, do
                                    # if 2, write to module log but not to 
                                    # stderr/stdout
#
# Logos of messages to export to client systems
#              Installation       Module       Message Type
 GetMsgLogo    INST_WILDCARD   MOD_WILDCARD    TYPE_TRACEBUF2
#GetMsgLogo    INST_WILDCARD   MOD_WILDCARD    TYPE_MSEED
# For TYPE_MSEED the miniSEED message must be 512-byte records, otherwise ignored.
 
 MaxMsgSize     4096          # maximum size (bytes) for input/output msgs
 QueueSize	 400          # max# messages in outgoing circular msg buffer

#
# Optional parameters
#
#Verbosity  0                 # set verbosity, useful for diagnostics
FlushLatency 30               # flush any buffered data streams idle for this many seconds
ReconnectInterval 10          # reconnect to ringserver at this interval in seconds


# List of station/channel/network/loc codes to process.
#--------------------------------------------------------
#
# Use any combination of Send_scnl (to send data as-is) and
#   Send_scnl_remap (to change the SCNL on the fly) commands.
# Use * as a wildcard for any field. A wildcard in the
#   "map to" fields of Send_scnl_remap means that field will
#   not be renamed.
#
#                  send SCNL     map to SCNL
# Send_scnl       JMP ASZ NC 01                # send this specific channel
# Send_scnl       JPS *   NC *                 # send all components of JPS NC
# Send_scnl_remap JGR VHZ NC --   *   EHZ * *  # change component code only
# Send_scnl_remap CAL *   NC *    ALM *   * *  # send all component of CAL, but
                                               # change the station code to ALM
# Send all SCNL in the WAVE_RING
Send_scnl * * * *
