#
#       Startstop (Unix Version -- Linux) Configuration File
#
#    <nRing> is the number of transport rings to create.
#    <Ring> specifies the name of a ring followed by it's size
#    in kilobytes, eg        Ring    WAVE_RING 1024
#    The maximum size of a ring depends on your operating system, 
#    amount of physical RAM and configured virtual (paging) memory 
#    available. A good place to start is 1024 kilobytes. 
#    Ring names are listed in file earthworm.d.
#
# refer to the wiki for how to change your specific system's shared memory
# size - if you encounter problems with large or too many rings, this is probably
# the issue.


 nRing               	4
 #Ring   WAVE_RING 	2048
 Ring   WAVE_RING 	4096
 Ring   PICK_RING 	1024
 Ring   HYPO_RING 	1024
 Ring   MUX_DATA_RING 	2048    # Added for PsnAdSend
#
 MyModuleId    MOD_STARTSTOP  # Module Id for this program
 HeartbeatInt  50             # Heartbeat interval in seconds
 MyClassName   OTHER             # For this program
 MyPriority     0             # For this program
 LogFile        1             # 1=write a log file to disk, 0=don't
 KillDelay      30            # seconds to wait before killing modules on
                              #  shutdown
 HardKillDelay  5             # number of seconds to wait on hard shutdown
                              #  for a child to respond to KILL signal
                              #  If missing or 0, no KILL signal will be sent
#  maxStatusLineLen   80     # Uncomment to specify length of lines in status
# statmgrDelay		2     # Uncomment to specify the number of seconds
					# to wait after starting statmgr 
					# default is 1 second

#
#
# Process          "pick_ew pick_ew.d"
# Class/Priority    OTHER 0
#
# Process          "binder_ew binder_ew.d"
# Class/Priority    OTHER 0
#
# Process          "eqproc eqproc.d"
# Class/Priority    OTHER 0
#
# Process          "diskmgr diskmgr.d"
# Class/Priority    OTHER 0
#
# Process          "copystatus WAVE_RING HYPO_RING"
## Class/Priority    OTHER 5
# Class/Priority    OTHER 0
#
# Process          "copystatus PICK_RING HYPO_RING"
## Class/Priority    OTHER 5
# Class/Priority    OTHER 0
#

# Statmgr to monitor for crashed processes
 Process          "statmgr statmgr.d"
 Class/Priority    OTHER 0

# PsnAdSend to read data from ADC24 board
 Process          "psnadsend PsnAdSend.d"
 Class/Priority    OTHER 0
#
# Send data to WinSDR application(s)
 Process          "ew2ws Ew2Ws.d"
 Class/Priority    OTHER 0

# Send WAVE_RING channels to remote ringserver
 Process          "ew2ringserver ew2ringserver.d"
 Class/Priority    OTHER 0

# Store WAVE_RING data to sdcard
# Process          "wave_serverV wave_serverV.d"
# Class/Priority    OTHER 0
#
# Send ring data to another EW system via their import_ack module
#Process          "export_ack export_ack.d"
#Class/Priority    OTHER 0
#
# Generate Helicorder GIF files
#Process          "heli_ewII_launch.sh heli_ewII.d"
#Class/Priority    OTHER 0
#
# Make sure the status messages written to MUX_DATA_RING get to the WAVE_RING
# that is monitored by statmgr
Process          "copystatus MUX_DATA_RING WAVE_RING"
Class/Priority    OTHER 0
