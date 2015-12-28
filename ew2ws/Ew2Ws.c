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
unsigned  tidListen, tidReceive, tidQueue;
time_t listenRestartTime;

mutex_t lsMx, rsMx, msgMx, userMx;

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
	
//char inBuffData[ 16384 ];		// fixme - same size as MAX_QUEUE_ELEM_SIZE
char outputData[ 16384 ];		// fixme - these need to be separate

int muxData[ 16 ][ 16384 ];
int channelSequence = -1;
double packetTime;

extern int m_length;

void KillTransmitThread( UserInfo *pUI );

// send may return early before sending all bytes. send it all.
ssize_t sendn( UserInfo *pUI, int sockfd, const void *buf, size_t len, int flags)
{
	int ret, bytes = 0;
	while (bytes < len) {
		ret = send(sockfd, buf+bytes, len-bytes, flags);
		if (ret < 0) {
			if( Debug > 1 )
				LogWrite("", "Send to %s:%u returned: %d, errno %d, %s\n", 
					pUI->ipaddr, pUI->port, ret, errno, strerror(errno));
			if( errno == EINTR ) {
				continue;
			}
			else if( errno == EAGAIN ) {
				sleep_ew( 100 );			
				continue;
			}
			else {
				return ret;
			}
		}
		if(ret != len-bytes) {
			if( Debug > 1 )
				LogWrite("", "Note: short send to %s:%u: req %d, sent %d\n", 
					pUI->ipaddr, pUI->port, len-bytes, ret);
		}
			
		bytes+=ret;
	}
	if(bytes != len) {
		LogWrite("", "couldn't send all bytes to %s:%u: req %d, sent %d\n", 
			pUI->ipaddr, pUI->port, len, bytes);
	}
	return bytes;
}

int SendLogMessage( UserInfo *pUI, char *data )
{
	// fixme - these need to be private
	PreHdr *phdr = (PreHdr *)outputData;
	MuxHdr *pMux = (MuxHdr *)data;
	char *msg = &data[ sizeof( MuxHdr ) ];
	int type24Bit = FALSE, len = strlen( msg ), plen;
	int outputLength;
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
		
	if( sendn( pUI, pUI->sock, outputData, outputLength, MSG_NOSIGNAL ) != outputLength )  {
		LogWrite("", "Socket %s:%u Send Error: %s\n", pUI->ipaddr, pUI->port, strerror(errno) );
		return 0;
	}	
	pUI->totalSentPackets++;
	
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
	int ret;
	int outputLength;
		
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
		
	if( (ret = sendn( pUI, pUI->sock, outputData, outputLength, MSG_NOSIGNAL )) != outputLength )  {
		LogWrite("", "Socket %s:%u Send Error: %d bytes, ret %d, %s\n", 
			pUI->ipaddr, pUI->port, outputLength, ret, strerror(errno) );
		return 0;
	}	
	pUI->totalSentPackets++;
	
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

	if( sendn( pUI, pUI->sock, sendLine, len, MSG_NOSIGNAL ) != len )  {
		LogWrite("", "Socket %s:%u Send Error: %s\n", pUI->ipaddr, pUI->port, strerror(errno) );
		return 0;
	}
	pUI->totalSentPackets++;
	return 1;
}	

/* Returns true on success, or false if there was an error */
int SetSocketBlockingEnabled(int fd, int blocking)
{
	if (fd < 0) 
		return 0;
#ifdef WIN32
	unsigned long mode = blocking ? 0 : 1;
	return (ioctlsocket(fd, FIONBIO, &mode) == 0) ? 1 : 0;
#else
	int flags = fcntl(fd, F_GETFL, 0);
	if (flags < 0) 
		return 0;
	flags = blocking ? (flags&~O_NONBLOCK) : (flags|O_NONBLOCK);
	return (fcntl(fd, F_SETFL, flags) == 0) ? 1 : 0;
#endif
}

int DiscardRx( UserInfo *pUI )
{
	char buf[1024];
	int ret, bytes = 0;

	// temporarily use non-blocking mode
	if( !SetSocketBlockingEnabled( pUI->sock, 0 ) ) {
		LogWrite("", "Failed setting non-blocking mode\n");
		return -1;		// failed for some reason
	}

	do {
		ret = recv( pUI->sock, buf, sizeof(buf), 0 );
		if( ret > 0 ) 
			bytes += ret;
	} while( ret > 0 );

	if( bytes > 0 && Debug > 2 )
		LogWrite("", "Discarded %d bytes from client %s:%u\n",
				bytes, pUI->ipaddr, pUI->port);

	if( !SetSocketBlockingEnabled( pUI->sock, 1 ) ) {
		LogWrite("", "Failed return to blocking mode\n");
		return -1;		// failed for some reason
	}
}

// tport_copyfrom() / getmsg() don't work with multiple threads.  I couldn't see how
// tport_buffer() could work with multiple reader threads either. So, instead, create a 
// single thread which copies data from the shared ring, into separate output queues for
// each network client.

thr_ret QueueManager( void *p )
{
	int i, sts;
	long msgSize;
	UserInfo *pUI;
	char inBuffData[ 16384 ];
	BYTE seq;
					
	if( Debug )
		LogWrite( "", "Starting QueueManager\n");

	/* Flush the incoming transport ring */
	while( tport_copyfrom( &InRegion, &logo, 1, &waveLogo, &msgSize, 
			inBuffData, sizeof( inBuffData ), &seq ) != GET_NONE );

	// fixme - can we skip this if no active clients are connected?

	/************************* main queueing loop *********************/
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

		if( Debug > 2 )
			LogWrite( "", "Queue %ld bytes\n", msgSize );

		RequestSpecificMutex(&userMx);
		for( i=0; i<MAX_CONNECT_USERS; i++) {
			pUI = &userInfo[ i ];	
			if( pUI->inUse ) {
				// fixme - handle race when shutting down TransmitThread
				if( enqueue(&pUI->q, inBuffData, msgSize, logo ) == 0) 
					SEM_POST(&pUI->q_sem);
				else if( Debug )
					LogWrite( "", "Couldn't enqueue %ld bytes!\n", msgSize );
			}
		}
		ReleaseSpecificMutex(&userMx);
	}

	LogWrite( "", "Shutdown QueueManager\n");
	
	KillSelfThread();

#ifdef WIN32
	return;
#else
	return 0;
#endif
}

thr_ret TransmitLoop( void *p )
{
	int ret, sts, len, c, first = 1;
	long msgSize;
	char sendLine[ 1024 ];
	UserInfo *pUI = ( UserInfo *)p;
	ConnectInfo *pCI;
	char nameStr[1024], tmp[ 256 ];
	char inBuffData[ 16384 ];		// FIXME - does this really need to be this big?
	char outputData[ 16384 ];
	MuxHdr *pMux = (MuxHdr *)inBuffData;
	BYTE seq;
	SHM_INFO myInRegion;
	MSG_LOGO logo, waveLogo;				
					
	pUI->updateTime = time( 0 );
	pUI->noDataReport = 0;
	pUI->recvPackets = 0;
	pUI->totalSentPackets = 0;
	pUI->connecting = FALSE;
	pUI->restart = pUI->connected = TRUE;

	/************************* main send loop *********************/
	while ( 1 )  {

		// dequeue is not a blocking read, so use counting semaphore
		SEM_WAIT( &pUI->q_sem );
		if(( ret = dequeue( &pUI->q, (void*)inBuffData, &msgSize, &logo )) < 0 ) {
			LogWrite( "", "dequeue returned %d!\n", ret);
			continue;		// empty
		}

		if( exitEw2Ws )
			break;
			
		if( Debug > 2 )
			LogWrite( "", "Dequeued %ld bytes\n", msgSize );

		if( first )  {
			first = 0;
			if( !SendInfoLine( pUI, (MuxHdr *)inBuffData ) )
				break;
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

		// WinSDR might be configured to send ACKs. Drain the Rx queue
		DiscardRx( pUI );

	}

	LogWrite( "", "Disconnecting client %s:%u. %u total packets sent\n", 
		pUI->ipaddr, pUI->port, pUI->totalSentPackets );
	
	CloseUserSock( pUI );
	KillTransmitThread( pUI );

#ifdef WIN32
	return;
#else
	return 0;
#endif
}

// called by ListenThread
UserInfo *NewUserInfo()
{
	UserInfo *pUI;
	int i;
	
	RequestSpecificMutex(&userMx);

	if( activeUsers >= MAX_CONNECT_USERS ) {
		ReleaseSpecificMutex(&userMx);
		return NULL;
	}

	for( i=0; i<MAX_CONNECT_USERS; i++) {
		pUI = &userInfo[ i ];	

		if( !pUI->inUse ) {
			memset( pUI, 0, sizeof( UserInfo ) );
			pUI->index = activeUsers++;
			pUI->inUse = TRUE;
			pUI->sock = SOCKET_ERROR;
			pUI->pCI = 0;
			initqueue( &pUI->q, MAX_QUEUE_LEN, MAX_QUEUE_ELEM_SIZE );
			SEM_INIT( &pUI->q_sem, 0, ~0 );		// FIXME
			ReleaseSpecificMutex(&userMx);
			return pUI;
		}
		
	}
	ReleaseSpecificMutex(&userMx);
	return NULL;
}

// called by TransmitThreads
void RemoveUserInfo( UserInfo *pUI )
{
	if( Debug )
		LogWrite( "", "RemoveUser at %d\n", pUI->index );
	
	RequestSpecificMutex(&userMx);

	pUI->inUse = FALSE;
	pUI->updateTime = 0; 
	pUI->restart = pUI->connected = pUI->connecting = FALSE;

	if( activeUsers )
		--activeUsers;

	ReleaseSpecificMutex(&userMx);
}

/* Listen for incoming connections */
thr_ret ListenThread( void *parm )
{
	int err, retval, timeout, addrSize = sizeof(struct sockaddr_in);
	struct timeval wait;
	struct sockaddr_in localAddr, peer;
	//fd_set rfds, wfds, efds, active_fds;
	fd_set rfds; 
	UserInfo *pUI;
	int i, sock;
	int enable = 1;
			
	if( Debug )
		LogWrite( "", "Ew2Ws Listen Thread Start\n" );
	
	listenRestartTime = time( 0 );
		
	if( ( listenSock = socket_ew( AF_INET, SOCK_STREAM, 0)) < 0 )  {
		LogWrite( "", "Error Opening Socket: %s. Exiting\n", strerror(listenSock) );
		ReportError( 7, "Socket Error");
		goto end;
	}
	
	if( setsockopt( listenSock, SOL_SOCKET, SO_REUSEADDR, &enable, sizeof(int)) < 0 )
		LogWrite( "", "setsockopt(SO_REUSEADDR) failed\n");

	memset( &localAddr, 0, sizeof(localAddr) );
	
	localAddr.sin_port = htons( Port );
	localAddr.sin_family = AF_INET;
	if( Host && strlen( Host ))
		localAddr.sin_addr.s_addr = inet_addr( Host );
	else 
		localAddr.sin_addr.s_addr = htonl(INADDR_ANY);
	
		
	if( ( err = bind_ew(listenSock, (struct sockaddr *)&localAddr, sizeof(localAddr))) < 0)  {
		LogWrite( "", "TCP/IP Socket Bind Failed on %s:%u: %s\n", 
			inet_ntoa(localAddr.sin_addr), ntohs(localAddr.sin_port), strerror(errno) );
		ReportError( 7, "Socket Error");
		goto end;
	}
		
	if( ( err = listen_ew( listenSock, 0 )) < 0)  {
		ReportError( 7, "Socket Error: %s", strerror(errno) );
		LogWrite( "", "TCP/IP Couldn't Get Listen Socket\n" );
		goto end;
	}
	
	LogWrite( "", "Ew2Ws listening on %s:%u\n", inet_ntoa(localAddr.sin_addr), ntohs(localAddr.sin_port));

	listenRestartTime = time( 0 );
		
	while( !exitListenThread )  {
		FD_ZERO( &rfds );
		//FD_ZERO( &wfds );
		//FD_ZERO( &efds );
		FD_SET( listenSock, &rfds );
		//FD_SET( listenSock, &wfds );
		//FD_SET( listenSock, &efds );

		/* block on socket activity */
		if( (retval = select_ew( listenSock+1, &rfds, NULL, NULL, 2000 ) ) < 0)  {
			LogWrite( "", "TCP/IP select Failed: %s\n", strerror(retval) );
			ReportError( 7, "Socket Error");
			break;
		}
		if( !retval )  {
			listenRestartTime = time( 0 );		// timeout occurred
			continue;
		}
		//LogWrite( "", "select returned %d\n", retval);
		
		/* service sockets with pending input */
		for( i=0; i<FD_SETSIZE; i++ ) {
			if( FD_ISSET( i, &rfds )) {
				if( i == listenSock ) {

					if( ! ( pUI = NewUserInfo() ) )  {
						LogWrite( "", "Too Many TCP/IP Users. %d connected already.\n", activeUsers );
						ReportError( 5, "Too Many TCP/IP Users");
						if((sock = accept_ew( listenSock, (struct sockaddr *)&peer, &addrSize, 500 ) ) >= 0)
							close(sock);		// immediately close it
						continue;
					}
					if(( pUI->sock = accept_ew( listenSock, (struct sockaddr *)&peer, &addrSize, 2000 ) ) < 0)  {
						LogWrite( "", "TCP/IP Accept Failed: %s\n", strerror(pUI->sock) );
						RemoveUserInfo( pUI );
						ReportError( 7, "Socket Error");
						break;
					}

					//FD_SET( pUI->sock, &active_fds );
					pUI->connecting = pUI->restart = TRUE;
					pUI->updateTime = pUI->connectTime = time( 0 );
					pUI->port = ntohs(peer.sin_port);
					strncpy(pUI->ipaddr, inet_ntoa(peer.sin_addr), sizeof(pUI->ipaddr));
					pUI->ipaddr[ sizeof(pUI->ipaddr)-1 ] = 0;
					
					LogWrite( "", "New client connection from %s:%u\n", pUI->ipaddr, pUI->port);

					if( StartThreadWithArg( TransmitLoop, pUI, (unsigned)THREAD_STACK, &pUI->tidReceive ) == -1 )  {
						LogWrite( "", "Error starting receive thread. Exiting.\n" );
						ReportError( 7, "Thread Start Error");
						RemoveUserInfo( pUI );
						break;
					}
				}
			}
		}
	}
	
end:
	exitListenAck = TRUE;
	KillListenThread();
	LogWrite( "", "Ew2Ws Listen Thread Done.\n" );

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

void KillTransmitThread( UserInfo *pUI )
{
	RemoveUserInfo( pUI );
	pUI->exitAck = TRUE;
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

void CheckStatus()
{
	int max, i, diff = 0, cnt, dspFlag = 0;
	MSG_LOGO recLogo;
	long msgLen, ret;
	char newMsg[256], ch;
	UserInfo *pUI;
	//ConnectInfo *pCI;
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
	
	LogWrite( "", "Ew2Ws Exiting with code %d after %u seconds\n", 
		exitcode, time(NULL)-start_time );
	
	DisplayReport();
	exit( exitcode );
}

void CntlHandler( int sig )
{
	/* if control-c clean up and exit program if ControlCExit = 1 */
	if( sig == 2 )  {
		if( ControlCExit )  {
			LogWrite( "", "Exiting Program...\n");
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

	CreateSpecificMutex( &lsMx );		// listen sock Mx
	CreateSpecificMutex( &rsMx );		// receive sock Mx
	CreateSpecificMutex( &userMx );		// add/remove user Mx
	CreateSpecificMutex( &msgMx );		// log message Mx
	
	exitListenAck = 0;
	
	activeUsers = 0;
	memset( (void*)userInfo, 0, sizeof( userInfo ) );
	for( i = 0; i != MAX_CONNECT_USERS; i++ )
		userInfo[i].sock = SOCKET_ERROR;
	
	for( i = 0; i != MAX_CHAN_LIST ; i++ )
		ChanList[i].sequenceNumber = -1;

	// fixme create struct for array of UserInfo and mutex.  Pass that ptr.
	if( StartThreadWithArg( QueueManager, NULL, (unsigned)THREAD_STACK, &tidQueue) == -1 )  {
		LogWrite( "", "Error starting Queue Manager thread. Exiting.\n" );
		ReportError( 7, "Thread Start Error");
		return 0;
	}

	return TRUE;
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
	
	if( Debug )
		LogWrite( "", "Starting Listen Thread\n");
		
	if( StartThread( ListenThread, (unsigned)THREAD_STACK, &tidListen ) == -1 )  {
		LogWrite( "e", "Error starting receive thread. Exiting.\n" );
		ReportError( 7, "Thread Start Error");
		tport_detach( &InRegion );
   		return -1;
	}

	while( 1 )  {
		// Exit if our ListenThread terminated for some reason
		if( exitListenAck ) {
			LogWrite( "", "Listen thread terminated\n" );
			break;
		}
		if( tport_getflag( &InRegion ) == TERMINATE || tport_getflag( &InRegion ) == MyPid )  {
			LogWrite( "", "Received terminate message" );
			break;
		}
		CheckStatus();
		sleep_ew( 1000 );
	}
	
	DisplayReport();
	ExitEw2Ws( 0 );
}
