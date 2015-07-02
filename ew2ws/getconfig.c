/*********************************************************************
*									getconfig.c	  					 *
*																	 *
*********************************************************************/

#include "Ew2Ws.h"

/* Function declaration */
int IsComment( char [] );	 // Defined below

/* The configuration file parameters */
unsigned char ModuleId;		// Module id of this program
char Host[256];				// Host name or IP Address of WinSDR system
int Port;					// Port to use when connection to WinSDR
int	ChanRate;			  	// Rate in samples per second per channel
long InKey;					// Key to ring where mux data will live
int HeartbeatInt;		 	// Heartbeat interval in seconds
int SocketTimeout = 60000;	// Time in milliseconds
int NoDataWaitTime = 45;	// Time to wait for no data. If no data reset recv thread. In seconds.
int RestartWaitTime = 60;	// Time to wait between reconnects. In seconds.
int Debug = 0;				// If found print debug info
int SendAck = 0;			// If true send ack packet after x received packets
int Nchans = 0;			 	// Number of channels in SCNL list below
SCNL ChanList[MAX_CHAN_LIST];	// Array to fill with SCNL values
int ConsoleDisplay;			// Windows Only, if 1 use console functions like SetPos()
							// to display process info.
int ControlCExit;			// if 0 program ignores control-c, if 1 exit program							
int RefreshTime;			// Console refresh time in seconds. ConsoleDisplay must be 1.
int CheckStdin;				// if 1 check for user input 

#define NCOMMAND	5		// Number of mandatory commands in the config file

int GetChanScnl()
{
	char *s;
	int len, i;
	char tmp[ 64 ];
		
	if( (s = k_str() ) == NULL )  {
		LogWrite("e", "Station Parse Error\n" );
		return 0;
	}
	len = strlen( s );
	if( !len || ( len > ( sizeof( ChanList[Nchans].sta ) - 1 ) ) )  {
		LogWrite("e", "Station Length Parse Error Max = %d\n", sizeof( ChanList[Nchans].sta ) - 1 );
		return 0;
	}
	strcpy( ChanList[Nchans].sta,  s );
		
	if( (s = k_str() ) == NULL )  {
		LogWrite("e", "Component Parse Error\n" );
		return 0;
	}
	len = strlen( s );
	if( !len || ( len > ( sizeof( ChanList[Nchans].comp ) - 1 ) ) )  {
		LogWrite("e", "Component Length parse Error Max = %d\n", sizeof( ChanList[Nchans].comp ) - 1 );
		return 0;
	}
	strcpy( ChanList[Nchans].comp,  s );
		
	if( (s = k_str() ) == NULL )  {
		LogWrite("e", "Network Parse Error\n" );
		return 0;
	}
	len = strlen( s );
	if( !len || ( len > ( sizeof( ChanList[Nchans].net ) - 1 ) ) )  {
		LogWrite("e", "Network Parse Length Error Max = %d\n", sizeof( ChanList[Nchans].net ) - 1 );
		return 0;
	}
	strcpy( ChanList[Nchans].net,  s );
	
	if( (s = k_str() ) == NULL )  {
		LogWrite("e", "Location Parse Error\n" );
		return 0;
	}
	len = strlen( s );
	if( !len || ( len > ( sizeof( ChanList[Nchans].loc ) - 1 ) ) )  {
		LogWrite("e", "Location Length Parse Error Max = %d\n", sizeof( ChanList[Nchans].loc ) - 1 );
		return 0;
	}
	strcpy( ChanList[Nchans].loc,  s );
	
	if( ( i = k_int() ) <= 1 )
		LogWrite("e", "Parse Error No ADC Bits to use, using default\n" );
	else  {
		if( i < 8 || i > 24	)
			LogWrite("e", "Parse Error ADC Bits range error, using default of 16\n" );
		else
			ChanList[Nchans].adcBits = i;
	}
		
	if( ( i = k_int() ) <= 0 )
		LogWrite("e", "Parse Error No ADC Gain, using default of 1\n" );
	else  {
		if( ( i != 1 ) && ( i != 2 ) && ( i != 4 ) && ( i != 8 ) && ( i != 16 ) && ( i != 32 ) && ( i != 64 ) )
			LogWrite("e", "Parse Error ADC Gain not 1,2,4,8,16,32, or 64, using default of 1\n" );
		else
			ChanList[Nchans].adcGain = i;
	}
		
	sprintf( ChanList[ Nchans ].testKey, "%s.%s.%s.%s", ChanList[Nchans].sta, ChanList[Nchans].comp, 
		ChanList[Nchans].net, ChanList[Nchans].loc );
	if( ++Nchans > MAX_CHAN_LIST )  {
		LogWrite( "e", "Too many channels defined in config file, max = %d\n", MAX_CHAN_LIST );
		return 0;
	}
	
	return TRUE;
}

int GetConfig( char *configfile )
{
	char init[NCOMMAND];	  /* Flags, one for each command */
	int nmiss;				  /* Number of commands that were missed */
	int	nfiles;
	int	i, cherr = 0;
	char str[ 256 ], tmp[ 256 ], *pLastCom = 0;

	// Set non mandatory defaults 
	ConsoleDisplay = 0;
	ControlCExit = 0;
	RefreshTime = 60;
	CheckStdin = 0;
		
	/* Set to zero one init flag for each required command */
	for ( i = 0; i < NCOMMAND; i++ )
		init[i] = 0;

	/* Open the main configuration file */
	nfiles = k_open( configfile );
	if ( nfiles == 0 )  {
		LogWrite( "", "Ew2Ws: Error opening configuration file <%s>\n", configfile );
		return -1;
	}

	/* Process all nested configuration files */
	while ( nfiles > 0 )  {			 	/* While there are config files open */
		while ( k_rd() )  {			  	/* Read next line from active file  */
			int  success;
			char *com;
			char *str;

			com = k_str();			 /* Get the first token from line */
			pLastCom = com;
			
			if ( !com ) continue;				 /* Ignore blank lines */
			if ( com[0] == '#' ) continue;	 /* Ignore comments */

			/* Open another configuration file */
			if ( com[0] == '@' )  {
				success = nfiles + 1;
				nfiles  = k_open( &com[1] );
				if ( nfiles != success )  {
					LogWrite( "", "Ew2Ws: Error opening command file <%s>.\n", &com[1] );
					return -1;
				}
				continue;
			}

			/* Read configuration parameters */
			else if ( k_its( "ModuleId" ) )  {
				if ( str = k_str() )  {
					if ( GetModId(str, &ModuleId) == -1 )  {
						LogWrite("", "Ew2Ws: Invalid ModuleId <%s>. Exiting.\n", str );
						return -1;
					}
				}
				init[0] = 1;
			}
			else if ( k_its( "Host" ) )  {
				str = k_str();
				strcpy( Host, str );
				init[1] = 1;
			}
			else if ( k_its( "Port" ) )  {
				Port = k_int();
				init[2] = 1;
			}
			else if ( k_its( "InRing" ) )  {
				if ( str = k_str() )  {
					if ( (InKey = GetKey(str)) == -1 )  {
						LogWrite("", "Ew2Ws: Invalid InRing <%s>. Exiting.\n", str );
						return -1;
					}
				}
				init[3] = 1;
			}
			else if ( k_its( "HeartbeatInt" ) )  {
				HeartbeatInt = k_int();
				init[4] = 1;
			}
			/* Option parameters */
			else if ( k_its( "SocketTimeout" ) )
				SocketTimeout = k_int() * 1000;
			else if ( k_its( "NoDataWaitTime" ) )
				NoDataWaitTime = k_int();
			else if ( k_its( "RestartWaitTime" ) )
				RestartWaitTime = k_int();
			else if ( k_its( "Debug" ) )
				Debug = k_int();
			else if ( k_its( "SendAck" ) )
				SendAck = k_int();
				
			else if ( k_its( "ConsoleDisplay" ))  {
				ConsoleDisplay = k_int();
			}
			else if ( k_its( "ControlCExit" ))  {
				ControlCExit = k_int();
			}
			else if ( k_its( "RefreshTime" ))  {
				RefreshTime = k_int();
			}
			else if ( k_its( "CheckStdin" ))  {
				CheckStdin = k_int();
			}
			/* Get the channel list */
			else if ( k_its( "Chan" ) )  {		// Scnl value for each channel
				if( !GetChanScnl() )  {
					cherr = TRUE;
					break;
				}
			}
			/* An unknown parameter was encountered */
			else  {
				LogWrite("", "Ew2Ws: <%s> unknown parameter in <%s>\n", com, configfile );
				return -1;
			}
			/* See if there were any errors processing the command */
			if ( k_err() )  {
				LogWrite("", "Ew2Ws: Bad <%s> command in <%s>.\n", com, configfile );
				return -1;
			}
		}
		nfiles = k_close();
	}
	if( cherr )  {
		if( pLastCom )
			LogWrite("", "PsnAdSend: Bad Parse Channel at <%s> in <%s>.\n", pLastCom, configfile );
		return -1;
	}

	/* After all files are closed, check flags for missed commands */
	nmiss = 0;
	for ( i = 0; i < NCOMMAND; i++ )
		if ( !init[i] )
			nmiss++;
	if ( nmiss > 0 )  {
		logit("", "Ew2Ws: ERROR, no " );
		if ( !init[0] ) logit("", "<ModuleId> " );
		if ( !init[1] ) logit("", "<Host> " );
		if ( !init[2] ) logit("", "<Port> " );
		if ( !init[3] ) logit("", "<OutRing> " );
		if ( !init[4] ) logit("", "<HeartbeatInt> " );
		logit("", "command(s) in <%s>.\n", configfile );
		return -1;
	}

	return 0;
}

void LogConfig( void )
{
	int i;
	char chr;

	logit( "", "ModuleId:        %u\n", ModuleId );
	logit( "", "Host:            %s\n", Host );
	logit( "", "Port:            %d\n", Port );
	logit( "", "InKey:           %d\n", InKey );
	logit( "", "HeartbeatInt:    %d\n", HeartbeatInt );
	logit( "", "RestartWaitTime: %d\n", RestartWaitTime );
	logit( "", "NoDataWaitTime:  %d\n", NoDataWaitTime );
	logit( "", "SocketTimeout:   %d\n", SocketTimeout );
	logit( "", "Debug:           %d\n", Debug );
	logit( "", "SendAck:         %d\n", SendAck );
	
	logit( "", "ConsoleDisplay:  %d\n", ConsoleDisplay );
	logit( "", "ControlCExit:    %d\n", ControlCExit );
	logit( "", "RefreshTime:     %d\n", RefreshTime );
	logit( "", "CheckStdin:      %d\n", CheckStdin );
	
	/* Log the channel list */
	logit( "", "\n" );
	logit( "", "chan Sta    Comp Net Loc Bits Gain\n" );
	logit( "", "---- -----  ---- --- --- ---- ----\n" );

	for ( i = 0; i < Nchans; i++ )  {
		logit( "", "%2d   %-5s  %-3s  %-2s  %-2s   %d   %d\n", i+1, ChanList[i].sta, ChanList[i].comp,
			ChanList[i].net, ChanList[i].loc, ChanList[i].adcBits, ChanList[i].adcGain );
	}
	logit("", "-------------------------------------------------------\n");
}

int IsComment( char string[] )
{
	int i;

	for ( i = 0; i < (int)strlen( string ); i++ )  {
		char test = string[i];
		if ( test!=' ' && test!='\t' )  {
			if ( test == '#'  )
				return 1;			 /* It's a comment line */
			else
				return 0;			 /* It's not a comment line */
		}
	}
	return 1;						 /* It contains only whitespace */
}
