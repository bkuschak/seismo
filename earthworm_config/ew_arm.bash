# Create an Earthworm environment on Linux, on Beaglebone Black!
# This file should be sourced by a bourne shell wanting 
# to run or build an EARTHWORM system under Linux.

# IMPORTANT NOTE, if running on a 64 bit linux system, long's can be 8 bytes and not 4 bytes!
# If this is the case, be sure to compile with the -m32 flag in the GLOBALFLAGS section!!!!

# for running EW on a linux box if any ports are used, make sure that your
# selected ports for wave_serverV or exports are below the range specified
# by your kernel for dynamic port allocation 
# (see sysctl net.ipv4.ip_local_port_range)

# Set environment variables describing your Earthworm directory/version

# Use value from elsewhere IF defined (eg from .bashrc)
# otherwise use the value after the :-
export EW_HOME="${EW_INSTALL_HOME:-/opt/earthworm}"
export EW_VERSION="${EW_INSTALL_VERSION:-earthworm_7.7}"
# Or set your own values directly and for certain
#export EW_HOME=/opt/earthworm
#export EW_VERSION=earthworm_svn
#EW_RUN_DIR="${EW_RUN_DIR:-$EW_HOME/run_working}"
EW_RUN_DIR="${EW_RUN_DIR:-$EW_HOME/$EW_VERSION/run_working}"
# Or set your own value directly
#EW_RUN_DIR=$EW_HOME/run_working

# this next env var is required if you run statmgr:
export SYS_NAME=`hostname`

# Set environment variables used by earthworm modules at run-time
# Path names must end with the slash "/"
export EW_INSTALLATION=INST_UNKNOWN
export EW_PARAMS="$EW_RUN_DIR/params/"
export EW_LOG="$EW_RUN_DIR/log/"
export EW_DATA_DIR="${EW_RUN_DIR}/data"


#set path=( ${EW_HOME}/${EW_VERSION}/bin $path )
export PATH="$EW_HOME/$EW_VERSION/bin:$PATH"


# Set environment variables for compiling earthworm modules
# add in -m32 if you are running a 64 bit linux architecture! Some EW codes may not work otherwise.
#
#export GLOBALFLAGS="-m32 -Dlinux -D__i386 -D_LINUX -D_INTEL -D_USE_SCHED  -D_USE_PTHREADS -D_USE_TERMIOS -I${EW_HOME}/${EW_VERSION}/include"
export GLOBALFLAGS="-Dlinux -D_LINUX -D_INTEL -D_USE_SCHED  -D_USE_PTHREADS -D_USE_TERMIOS -I${EW_HOME}/${EW_VERSION}/include"
export PLATFORM="LINUX"

export LINK_LIBS="-lm -lpthread"
export KEEP_STATE=""

# Set initial defaults
export CFLAGS=$GLOBALFLAGS
export CPPFLAGS=$GLOBALFLAGS
# be explicit about which compiler to use
export CC=`which gcc`

# Auto-detect fortran compiler and flags
# We simply use whichever we find first in: g77, f77, gfortran
#export FFLAGS="-m32"
export FFLAGS=""
if which gfortran 1> /dev/null 2>&1
then
    export FC=`which gfortran`
elif which g77 1> /dev/null 2>&1
then
    export FC=`which g77`
elif which f77 1> /dev/null 2>&1
then
    export FC=`which f77`
fi

# Alternatively, you can hard-code values here:
#export FC='...'
#export FFLAGS='...'
