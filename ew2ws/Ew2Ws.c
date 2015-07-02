/*********************************************************************
*									Ew2Ws.c						     *
* 																	 *
*********************************************************************/

#include "Ew2Ws.h"

/* Global variables */
SHM_INFO InRegion;						// Info structure for input region
int MyPid;								// process id, sent with heartbeat
unsigned char InstId;					// Installation id placed in the trace header
MSG_LOGO logo, waveLogo;				// Logo of messages 

SOCKET listenSock = SOCKET_ERROR;		// Listener Socket
int exitListenThread = 0, exitListenAck = 0;
unsigned  tidListen, tidReceive;
time_t listenRestartTime;

mutex_t lsMx, rsMx;

unsigned int sampleCount = 0;		// Scan number of samples processed
int noDataCounter = 0;
int firstPacket = 1;

/* Messages to display onthe screen are placed in this array */
char messages[ MAX_MESSAGES ][ MESSAGE_LEN ];
int numberMessages = 0;

char reportString[ MAX_RPT_STR_LEN ];
int reportStringLen;

UserInfo userInfo[ MAX_CONNECT_USERS ];
int activeUsers = 0;

time_t start_time;
int displayCount = 0;

int exitEw2Ws = 0;

ConnectInfo connectInfo[ MAX_CONNECT_USERS ];
	
static BYTE hdrStr[] = { 0xaa, 0x55, 0x88, 0x44 };

int packetID = 0;
	
char inBuffData[ 16384 ];
char outputData[ 16384 ];
int outputLength;

int muxData[ 16 ][ 16384 ];
int channelSequence = -1;
double packetTime;

extern int m_length;

int SendLogMessage( UserInfo *pUI, char *data )
{
	PreHdr *phdr = (PreHdr *)outputData;
	MuxHdr *pMux = (MuxHdr *)data;
	char *msg = &data[ sizeof( MuxHdr ) ];
	int type24Bit = FALSE, len = strlen( msg ), plen;
	BYTE crc;
		
	memcpy( phdr->hdr, hdrStr, 4);	// make the header
	phdr->type = 'L';
		
	if( pMux->boardType == 5 )  {
		type24Bit = TRUE;
		phdr->flags = 0xc0;
	}
	else if( pMux->boardType == 4 )
		phdr->flags = 0x81;
	else if( pMux->boardType == 3 )  {
		type24Bit = TRUE;
		phdr->flags = 0x40;
	}
	else if( pMux->boardType == 2 )
		phdr->flags = 0x80;
	else
		phdr->flags = 0x00;
	
	memcpy( &outputData[ sizeof(PreHdr) ], msg, len + 1 );
	
	plen = len + 1;
	phdr->len = plen + 1;			// 1 more for crc
	crc = CalcCRC( &outputData[4], plen + 4 );
	outputData[ sizeof(PreHdr) + plen ] = crc; 
	outputLength = plen + sizeof(PreHdr) + 1;
		
	if( send( pUI->sock, outputData, outputLength, 0 ) != outputLength )  {
		LogWrite("", "Socket Send Error\n");
		return 0;
	}	
	
	return 1;
}

int SendDataPacket( UserInfo *pUI, char *data, int length )
{
	PreHdr *phdr = (PreHdr *)outputData;
	MuxHdr *pMux = (MuxHdr *)data;
	DataHeader *pHdr = (DataHeader *)&data[ sizeof( MuxHdr ) ];
	int plen, type24Bit = 0, c, samples, index;
	short *spData;		// used to demux 16 bit data
	int *lpData;		// used to demux 32 bit data
	BYTE crc;
		
	memcpy( phdr->hdr, hdrStr, 4);	// make the header
	phdr->type = 'D';
		
	if( pMux->boardType == 5 )  {
		type24Bit = TRUE;
		phdr->flags = 0xc0;
	}
	else if( pMux->boardType == 4 )
		phdr->flags = 0x81;
	else if( pMux->boardType == 3 )  {
		type24Bit = TRUE;
		phdr->flags = 0x40;
	}
	else if( pMux->boardType == 2 )
		phdr->flags = 0x80;
	else
		phdr->flags = 0x00;
	
	memcpy( &outputData[ sizeof(PreHdr) ], pHdr, sizeof( DataHeader ) );
	
	/* Now demux the data */
	samples = pMux->sampleRate;
	if( type24Bit )  {
		lpData = (int *)&data[ sizeof( MuxHdr) + sizeof( DataHeader ) ];
		index = 0;
		while( samples-- )  {
			for( c = 0; c != pMux->numChannels; c++ )
				muxData[ c ][ index ] = *lpData++;
			++index;
		}
	}
	else  {
		spData = (short *)&data[ sizeof( MuxHdr ) + sizeof( DataHeader ) ];;
		index = 0;
		while( samples-- )  {
			for( c = 0; c != pMux->numChannels; c++ )
				muxData[ c ][ index ] = *spData++;
			++index;
		}
	}	
	
	InitPacker( &outputData[ sizeof(PreHdr) + sizeof( DataHeader ) ], Nchans, pMux->sampleRate, type24Bit );
	for( c = 0; c != Nchans; c++ )
		Pack( c, muxData[c] );
	
	plen = m_length + sizeof( DataHeader );
	phdr->len = plen + 1;			// 1 more for crc
	crc = CalcCRC( &outputData[4], plen + 4 );
	outputData[ sizeof(PreHdr) + plen ] = crc; 
	outputLength = plen + sizeof(PreHdr) + 1;
		
	if( send( pUI->sock, outputData, outputLength, 0 ) != outputLength )  {
		LogWrite("", "Socket Send Error\n");
		return 0;
	}	
	
	return 1;
}

int SendInfoLine( UserInfo *pUI, MuxHdr *pMux )
{	
	char nameStr[ 256 ], tmp[ 256 ], sendLine[ 1024 ];
	int first = 1, c, len;
	
	nameStr[0] = 0;
	for( c = 0; c != Nchans; c++ )  {
		sprintf( tmp, "%s=%s:%s:%s:%d:%d", ChanList[c].sta, ChanList[c].comp, 
			ChanList[c].net, ChanList[c].loc, ChanList[c].adcBits, ChanList[c].adcGain );
		if( first )
			first = 0;
		else
			strcat( nameStr, "|" );
		strcat( nameStr, tmp );	
	}
	sprintf( sendLine, "SPS: %d NumChans: %d Names: %s BrdType: %d", pMux->sampleRate, 
		Nchans, nameStr, pMux->boardType );
	len = strlen( sendLine ) + 1;
	if( send( pUI->sock, sendLine, len, 0 ) != len )  {
		LogWrite( "", "Send Error\n" );
		return 0;
	}
	return 1;
}	

thr_ret ReceiveLoop( void *p )
{
	int ret, sts, len, sendIt, c, first = 1;
	long msgSize;
	char sendLine[ 1024 ];
	UserInfo *pUI = ( UserInfo *)p;
	ConnectInfo *pCI;
	char nameStr[1024], tmp[ 256 ];
	MuxHdr *pMux = (MuxHdr *)inBuffData;
	BYTE seq;
					
	pUI->updateTime = time( 0 );
	pUI->noDataReport = 0;
	pUI->recvPackets = 0;
	pUI->totalRecvPackets = 0;
	
	activeUsers = 1;
	firstPacket = 1;
	
	LogWrite("", "Connected to WinSDR at %s:%d\n", pUI->who, Port );
	
	pCI = FindOrAddUser( pUI, TRUE );
	if( !pCI )  {
		LogWrite("", "Can't Add User %s, Too many connections\n", pUI->who );
		ReportError( 5, "Too Many Connections");
		CloseUserSock( pUI );
		KillReceiveThread( pUI );
		goto end;
	}
	pCI->pUI = pUI;
	pUI->pCI = pCI;
	++pCI->connectCount;
	
	pUI->connecting = FALSE;
	pUI->restart = pUI->connected = TRUE;

	/* Flush the incoming transport ring */
	while( tport_copyfrom( &InRegion, &logo, 1, &waveLogo, &msgSize, 
			inBuffData, sizeof( inBuffData ), &seq ) != GET_NONE );

	/************************* main send loop *********************/
	while ( 1 )  {
		sts = tport_getflag( &InRegion );
		if( sts == TERMINATE || sts == MyPid || exitEw2Ws )
			break;
		
		sts = tport_copyfrom( &InRegion, &logo, 1, &waveLogo, &msgSize, inBuffData, 
			sizeof( inBuffData ), &seq );
			
		if( sts == GET_NONE )  {
			sleep_ew( 100 );			
			continue;
		}		
		if( first )  {
			first = 0;
			SendInfoLine( pUI, (MuxHdr *)inBuffData );
		}
		
		if( pMux->msgType == 'D' )  {
			if( !SendDataPacket( pUI, inBuffData, msgSize ) )
				break;
		}
		else if( pMux->msgType == 'L' )  {
			if( !SendLogMessage( pUI, inBuffData ) )
				break;
		}
		else  {
			LogWrite( "", "Unknown message type %d\n", pMux->msgType );
		}
	}
	
	LogWrite( "", "Exit ReceiveLoop\n" );
	
	CloseUserSock( pUI );
	KillReceiveThread( pUI );

end:
#ifdef WIN32
	return;
#else
	return 0;
#endif
}

UserInfo *GetUserInfo()
{
	UserInfo *pUI;
	int i;
	
	pUI = &userInfo[ 0 ];	
	memset( pUI, 0, sizeof( UserInfo ) );
	pUI->inUse = TRUE;
	pUI->sock = SOCKET_ERROR;
	pUI->pCI = 0;
	strcpy( pUI->who, Host );
	return pUI;
}

void RemoveUserInfo( UserInfo *pUI )
{
	if( Debug )
		LogWrite( "", "RemoveUser at %d\n", pUI->index );
	
	pUI->inUse = FALSE;
	pUI->updateTime = 0; 
	pUI->restart = pUI->connected = pUI->connecting = FALSE;
	
	if( pUI->pCI )  {
		ConnectInfo *pCI = (ConnectInfo *)pUI->pCI;	
		pCI->pUI = 0;
	}	
	pUI->pCI = 0;
	
	if( activeUsers )
		--activeUsers;

}

thr_ret ListenThread( void *parm )
{
	int err, retval, timeout, addrSize = sizeof(struct sockaddr_in);
	struct timeval wait;
	struct sockaddr_in localAddr, peer;
	fd_set rfds, wfds;
	UserInfo *pUI;
			
	LogWrite( "", "Ew2Ws Listen Thread Start\n" );
	
	listenRestartTime = time( 0 );
		
	if( ( listenSock = socket_ew( AF_INET, SOCK_STREAM, 0)) == -1 )  {
		LogWrite( "", "Error Opening Socket. Exiting\n" );
		ReportError( 7, "Socket Error");
		KillListenThread();
		return;
	}
	
	memset( &localAddr, 0, sizeof(localAddr) );
	
	localAddr.sin_port = htons( Port );
	localAddr.sin_family = AF_INET;
	localAddr.sin_addr.s_addr = htonl(INADDR_ANY);
		
	if( ( err = bind_ew(listenSock, (struct sockaddr *)&localAddr, sizeof(localAddr))) == SOCKET_ERROR )  {
		LogWrite( "", "TCP/IP Socket Bind Failed\n" );
		ReportError( 7, "Socket Error");
		KillListenThread();
		goto end;
	}
		
	if( listen_ew( listenSock, 0 ) == SOCKET_ERROR)  {
		ReportError( 7, "Socket Error");
		LogWrite( "", "TCP/IP Couldn't Get Listen Socket\n" );
		KillListenThread();
		goto end;
	}
	
	sampleCount = 0;
	
	listenRestartTime = time( 0 );
		
	while( !exitListenThread )  {
		FD_ZERO( &rfds );
		FD_ZERO( &wfds );
		FD_SET( listenSock, &rfds );
		FD_SET( listenSock, &wfds );
		if( (retval = select_ew( listenSock+1, &rfds, &wfds, NULL, 2000 ) ) == SOCKET_ERROR )  {
			LogWrite( "", "TCP/IP select Failed\n" );
			ReportError( 7, "Socket Error");
			break;
		}
		
		if( !retval )  {
			listenRestartTime = time( 0 );
			continue;
		}
		
		if( ! ( pUI = GetUserInfo() ) )  {
			LogWrite( "", "Too Many TCP/IP Users\n" );
			ReportError( 5, "Too Many TCP/IP Users");
			continue;
		}
		LogWrite( "", "New User at %d\n", pUI->index );
		
		if(( pUI->sock = accept_ew( listenSock, (struct sockaddr *)&peer, &addrSize, 2000 ) ) == SOCKET_ERROR )  {
			LogWrite( "", "TCP/IP Accept Failed\n" );
			RemoveUserInfo( pUI );
			ReportError( 7, "Socket Error");
			break;
		}
		
		pUI->connecting = pUI->restart = TRUE;
		pUI->updateTime = pUI->connectTime = time( 0 );
		
		if( StartThreadWithArg( ReceiveLoop, pUI, (unsigned)THREAD_STACK, &pUI->tidReceive ) == -1 )  {
			LogWrite( "", "Error starting receive thread. Exiting.\n" );
			ReportError( 7, "Thread Start Error");
			RemoveUserInfo( pUI );
			break;
      	}
	}
	
	LogWrite( "", "Ew2Ws Listen Thread Done.\n" );
	
	exitListenAck = TRUE;
	
	KillListenThread();

end:
#ifdef WIN32
	return;
#else
	return 0;
#endif
}

void CloseUserSock( UserInfo *pUI )
{
	RequestSpecificMutex(&rsMx);
	
	if( pUI->sock != SOCKET_ERROR )
		closesocket_ew( pUI->sock, SOCKET_CLOSE_IMMEDIATELY_EW );
	pUI->sock = SOCKET_ERROR;
	
   	ReleaseSpecificMutex( &rsMx );

	pUI->connected = pUI->connecting = 0;
	
}

void KillReceiveThread( UserInfo *pUI )
{
	RemoveUserInfo( pUI );
	pUI->exitAck = TRUE;
	activeUsers = 0;
	KillSelfThread();
}

void KillListenThread()
{
	RequestSpecificMutex(&lsMx);
	
	if( listenSock != SOCKET_ERROR )
		closesocket_ew(listenSock, SOCKET_CLOSE_IMMEDIATELY_EW);
	listenSock = SOCKET_ERROR;
	
   	ReleaseSpecificMutex( &lsMx );
	
	listenRestartTime = time( 0 );
	KillSelfThread();
}

void CheckConnectStatus( UserInfo *pUI, time_t now )
{
	time_t diff = now - pUI->updateTime;
	if( diff >= NoDataWaitTime )  {
		LogWrite( "", "%s No Data Timeout\n", pUI->who );
		ReportError( 2, "%s No Data Timeout", pUI->who );
		pUI->exitThread = TRUE;
	}
}

void CheckStatus()
{
	int max, i, diff = 0, cnt, dspFlag = 0;
	MSG_LOGO recLogo;
	long msgLen, ret;
	char newMsg[256], ch;
	UserInfo *pUI;
	ConnectInfo *pCI;
	time_t now;
		
	now = time( 0 );
	Heartbeat( now );		/* Beat the heart once per second */
	
#ifdef WIN32
	if( CheckStdin )  {
		dspFlag = 0;
		while( kbhit() )  {
			ch = getch();
			if( ch == 'c' || ch == 'C' )  {
				if( ConsoleDisplay )
					ClearScreen();
				memset( messages, 0, sizeof( messages ) );
				numberMessages = 0;
				ClearUserData();
			}
			dspFlag = TRUE;
		}
		if( dspFlag )  {
			DisplayReport();
			displayCount = 0;
		}
	}
#endif
		
	if( RefreshTime && ( ++displayCount >= RefreshTime ) )  {
		displayCount = 0;
		DisplayReport();
	}
}

void ms_log( int level, char *pszFormat, ... )
{
	int retval;
	char buff[ 1024 ];
	va_list varlist;
	va_start( varlist, pszFormat );
	vsprintf( buff, pszFormat, varlist );
	va_end (varlist);
	LogWrite( "", "(%d) %s\n", level,  buff );
}

void ExitEw2Ws( int exitcode )
{
	int i, max = 100;

	exitEw2Ws = TRUE;
	
	exitListenThread = TRUE;
	while( max-- )  {
		if( exitListenAck )
			break;
		sleep_ew( 50 );
	}
	
	for( i = 0; i != MAX_CONNECT_USERS; i++ )
		userInfo[ i ].exitThread = TRUE;
	max = 100;
	while( max-- )  {
		if( !activeUsers )
			break;
		sleep_ew( 50 );
	}

	/* Clean up and exit program */
	tport_detach( &InRegion );
	
	LogWrite( "", "Ew2Ws Exiting\n" );
	
	exit( exitcode );
}

void CntlHandler( int sig )
{
	/* if control-c clean up and exit program if ControlCExit = 1 */
	if( sig == 2 )  {
		if( ControlCExit )  {
			LogWrite( "", "Exiting Program...\n");
			DisplayReport();
			ExitEw2Ws( -1 );
		}
		else
			signal(sig, SIG_IGN);
	}
}

int InitEw2Ws( char *configFile )
{
	int i;
	
	start_time = time( NULL );
	
	memset( messages, 0, sizeof( messages ) );
	numberMessages = 0;
	memset( connectInfo, 0, sizeof( connectInfo ) );
		
	signal( SIGINT, CntlHandler );
	
	/* Initialize name of log-file & open it */
	logit_init( configFile, 0, 256, 1 );

	/* Read configuration parameters */
	if ( GetConfig( configFile ) < 0 )  {
		printf("Ew2Ws: Error reading configuration file. Exiting.\n");
		logit( "e", "Ew2Ws: Error reading configuration file. Exiting.\n");
		return 0;
	}

	/* Initialize the console display */
	if( ConsoleDisplay )
		InitCon();

	/* Set up the logo of outgoing waveform messages */
	if ( GetLocalInst( &InstId ) < 0 )  {
		LogWrite( "e", "Ew2Ws: Error getting the local installation id. Exiting.\n" );
		return 0;
	}
	LogWrite( "", "Local InstId:	 %u\n", InstId );

	/* Log the configuration file */
	LogConfig();

	/* Get our Process ID for restart purposes */
	MyPid = getpid();
	if( MyPid == -1 )  {
		LogWrite("e", "Ew2Ws: Cannot get PID. Exiting.\n" );
		return 0;
	}
	
	logo.instid = InstId;
	logo.mod = WILD;
	GetType( "TYPE_ADBUF", &logo.type );

	/* Attach to existing transport ring and send first heartbeat */
	tport_attach( &InRegion, InKey );
	LogWrite( "", "Attached to transport ring: %d\n", InKey );
	
	Heartbeat( start_time );

	/* Init tcp stuff */
	if( !InitSocket() )  {
		tport_detach( &InRegion );
		LogWrite( "", "InitSocket Error\n" );
		return 0;
	}

	CreateSpecificMutex( &lsMx );		// listen sock Mx
	CreateSpecificMutex( &rsMx );		// receive sock Mx
	
	exitListenAck = 0;
	sampleCount = 0;
	
	activeUsers = 0;
	memset( userInfo, 0, sizeof( userInfo ) );
	for( i = 0; i != MAX_CONNECT_USERS; i++ )
		userInfo[i].sock = SOCKET_ERROR;
	
	for( i = 0; i != MAX_CHAN_LIST ; i++ )
		ChanList[i].sequenceNumber = -1;
	return TRUE;
}

ConnectInfo *FindOrAddUser( UserInfo *pUI, int addOk )
{
	ConnectInfo *pCI;
	int i;
	
	for( i = 0; i != MAX_CONNECT_USERS; i++ )  {
		pCI = &connectInfo[ i ];
		if( !strcmp( pUI->who, pCI->who ) )  {
			return pCI;
		}
	}
		
	if( !addOk )
		return NULL;
		
	for( i = 0; i != MAX_CONNECT_USERS; i++ )  {
		pCI = &connectInfo[ i ];
		if( !pCI->who[0] )  {
			strcpy( pCI->who, pUI->who );
			pCI->connectCount = 0;
			return pCI;
		}
	}
	return NULL;
}

int main( int argc, char *argv[] )
{
	UserInfo *pUI;
	int dspTime = 0, msgSize, sts;
					
	/* Get command line arguments */
	if ( argc < 2 )  {
		printf( "Usage: Ew2Ws <config file>\n" );
		return -1;
	}

	if( !InitEw2Ws( argv[1] ) )
		return -1;
	
	LogWrite( "", "Starting Listen Thread\n");
		
	if( StartThread( ListenThread, (unsigned)THREAD_STACK, &tidListen ) == -1 )  {
		LogWrite( "e", "Error starting receive thread. Exiting.\n" );
		ReportError( 7, "Thread Start Error");
		tport_detach( &InRegion );
   		return -1;
	}

	while( 1 )  {
		if( tport_getflag( &InRegion ) == TERMINATE || tport_getflag( &InRegion ) == MyPid )  {
			LogWrite( "", "Received terminate message" );
			break;
		}
		CheckStatus();
		sleep_ew( 1000 );
	}
	
	ExitEw2Ws( 0 );
}
