                    -  DRF2TXT.exe program readme file  - 

Drf2Txt ( Daily Record File Two Text) utility is a 32-Bit command line program used to
save A/D data from a WinSDR daily record file to a text file. The program is compiled 
to run on 32 or 64 bit version of Window (XP to Win10). Drf2Txt can be used on DRF 
(Daily Record File) created using PSN 16-Bit or 24-Bit A/D boards.

Setup:

Drf2Txt needs access to the WinSDR configuration files used to create the DRF. The 
easiest way to use the program is to run it from your WinSDR root directory. If you 
run it from a different directory you will need to copy all of your *.ini files 
to the Drf2Txt directory. This includes the main WinSDR.ini file as well as all 
of the channel configuration files.

Usage:

Since Drf2Txt is a command line program you will need to open a DOS box and run 
the program from there. At minimum the program requires two input parameters, 
the start date and time and the number of minutes to save.

    Example: drf2txt 031215_122034 10

This will save 10 minutes worth of data starting at 03/12/2015 at 12:20:34 UTC. 
The format of the start date/time is MMDDYY_hhmmss where:

    MM = Month ( 1 to 12 )
    DD = Day ( 1 to 31 )
    YY = Year Note: The year is optional
    hh = hours past midnight
    mm = minutes past midnight
    ss = seconds past midnight Note: Seconds are optional

By default drf2txt uses UTC time. If the -l option is used the program will 
convert the start time from local time to UTC time.

Command Line Options:

    -o output_file_name	
        Output file name. If not specified the program will use the following 
	name format: MMDDYY_hhmmss.txt
    -d n
        Down sample the data by a factor of n. Example, if WinSDR is configured to
        record data at 100 SPS and the user enters a value to 4 the output will be 
        down sampled to 25 SPS.
    -c channel_id
        Used to save data from one channel. The channel ID is the string used to 
	identify the channel that is set in WinSDR's Channel Settings / Save File tab / 
	Sensor ID and File Name field.
    -w iniFileName
        Used to overwrite the default WinSDR configuration file name. If not specified 
	the program will use winsdr.ini.
    -h
        Used to dump the DRF header to the screen.
    -f
        Used to add additional header information to the output file.
    -p
        Used to save the header information in the PSN Text File format so the 
        output file can viewed using WinQuake.
    -l
        Used to convert the input start time from local time to UTC.
    -n
        Used to suppress any header information to the output file.
    -v
        Displays program version.
    -t
        Saves the sample time offset from start time as the first column in the output file. 
    
    -T
        Add sample time (UNIX time) to output file.
	
    -s 
    	Use space-separated instead of comma-separated values
    
    -P	
    	Override path to WinSDR root directory.
	
    -R
	Override path to WinSDR daily record file directory.	
	
Output File Format:

By default drf2txt will save all channels to the output file with one sample period 
per line. So if the user is recording 4 channels you will see 4 samples per line. 

    Example without the -t option:
        1,2,-2,-376
        5,2,-1,-325
        5,1,0,-262
        4,0,2,-192
        3,0,2,-118
 
    Example with the -t option at 200 SPS:
        0.000,1,2,-2,-376
        0.005,5,2,-1,-325
        0.010,5,1,0,-262
        0.015,4,0,2,-192
        0.020,3,0,2,-118


If the user specifies one channel to save using the -c option, or the user is 
recording just one channel, you will see one sample per line in the output file.

Version 1.1:
	Fixed a problem when requesting a start time around 00:00:00.
	Added -v and -t options.

Version 1.4:
	Fixed a problem with decoding VolksMeter Daily Record files.

-End
