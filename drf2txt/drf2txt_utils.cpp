/* drf2txt_utils.cpp - Save data from a winsdr daily record file to a text file */

#include "drf2txt.h"

#if !defined(_WIN32) && !defined(_WIN64)
#define _mkgmtime timegm
#endif

extern ChannelInfo channelInfo[ MAX_CHANNELS ];
extern int numberOfChannels, systemNumber;
extern char recordFilePath[ 256 ];
extern char winSdrPath[ 256 ];
extern time_t userStartTime;
extern int secondsToSave, useLocalTime;
extern HdrBlock hdrBlock;
extern int saveOneChannel, savingDataFlag;
extern char wsIniFile[ 256 ];
extern double sampleDelta, sampleTmAcc;

/* Parse the time entered by the user */
time_t ParseStartTime( char *inStr )
{
	int len, mon, day, year, hour, min, sec;
	time_t t;
	struct tm *nt;
	char tmp[ 256 ], num[ 3 ], *ptr;
		
	strcpy( tmp, inStr );					// make a copy of the start time string
	time( &t );							// get the current time if we need the year
	nt = gmtime( &t );
	
	year = nt->tm_year % 100;			// set default year
	if( ( ptr = strchr( tmp, '_' ) ) == NULL )  {
		printf("_ not found in date string\n");
		return 0;
	}
	*ptr++ = 0;
	
	// Get mon, day and optional year
	len = strlen( tmp );
	if( len != 4 && len != 6 )  {
		printf("First part of date string needs to be 4 or 6 characters.\n");
		return 0;
	}
	num[2] = 0;
	num[0] = tmp[0]; num[1] = tmp[1];
	mon = atoi( num );
	
	num[0] = tmp[2]; num[1] = tmp[3];
	day = atoi( num );
	if( len == 6 )  {				// need to get the year
		num[0] = tmp[4]; num[1] = tmp[5];
		year = atoi( num );
	}
	
	// now get the start time hour and minute
	len = strlen( ptr );
	if( len != 4 && len != 6 )  {
		printf("Second part of date string needs to be 4 or 6 characters.\n");
		return 0;
	}
	num[2] = 0;
	num[0] = ptr[0]; num[1] = ptr[1];
	hour = atoi( num );
	
	num[0] = ptr[2]; num[1] = ptr[3];
	min = atoi( num );
	
	sec = 0;
	if( len == 6 )  {
		num[0] = ptr[4]; num[1] = ptr[5];
		sec = atoi( num );
	}
	
	printf("Start Time: %d/%d/%d %02d:%02d:%02d\n", mon, day, year, hour, min, sec );
	if( useLocalTime )
		return MakeLocalTime( mon, day, year+2000, hour, min, sec );
	return MakeTime( mon, day, year+2000, hour, min, sec );
}

/* Find a key in the ini file and return its data as a double */
int GetParamDouble( char *fileName, char *key, double *to )
{
	FILE *fp;
	int found = 0;
	char str[ 256 ], *ptr;
		
	// Open the ini file
	if( ( fp = fopen( fileName, "r" ) ) == NULL )  {
		printf("GetParamDouble: Ini file %s not found\n", fileName );
		return 0;
	}
	// now find the key
	while( fgets( str, 256, fp ) != NULL )  {
		if( strstr( str, key ) )  {
			found = TRUE;
			break;
		}
	}
	fclose( fp );
		
	// exit if key not found
	if( !found )  {
		printf("GetParamDouble: Key %s not found in file %s\n", key, fileName );
		return 0;
	}
	// remove \n or \r from string	
	if( ( ptr = strchr( str, '\n') ) != NULL )
		*ptr = 0;
	if( ( ptr = strchr( str, '\r') ) != NULL )
		*ptr = 0;
	
	// find the = char
	if( ( ptr = strchr( str, '=' ) ) == NULL )  {
		printf("GetParamDouble: = not found in key %s\n", key );
		return 0;
	}
	++ptr;						// skip =
	*to = atof( ptr );			// convert to number
	return TRUE;
}

/* Find a key in the ini file and return its data as a int */
int GetParamInt( char *fileName, char *key, int *to )
{
	FILE *fp;
	int found = 0;
	char str[ 256 ], *ptr;
		
	// Open the ini file
	if( ( fp = fopen( fileName, "r" ) ) == NULL )  {
		printf("GetParamInt: Ini file %s not found\n", fileName );
		return 0;
	}
	// now find the key
	while( fgets( str, 256, fp ) != NULL )  {
		if( strstr( str, key ) )  {
			found = TRUE;
			break;
		}
	}
	fclose( fp );
		
	// exit if key not found
	if( !found )  {
		printf("GetParamInt: Key %s not found in file %s\n", key, fileName );
		return 0;
	}
	// remove \n or \r from string	
	if( ( ptr = strchr( str, '\n') ) != NULL )
		*ptr = 0;
	if( ( ptr = strchr( str, '\r') ) != NULL )
		*ptr = 0;
	
	// find the = char
	if( ( ptr = strchr( str, '=' ) ) == NULL )  {
		printf("GetParamInt: = not found in key %s\n", key );
		return 0;
	}
	++ptr;						// skip =
	*to = atoi( ptr );			// convert to number
	return TRUE;
}

/* Find a key in the ini file and return its data as a string */
int GetParamString( char *fileName, char *key, char *to )
{
	FILE *fp;
	int found = 0;
	char str[ 256 ], *ptr;
		
	// Open the ini file
	if( ( fp = fopen( fileName, "r" ) ) == NULL )  {
		printf("GetParamString: Ini file %s not found\n", fileName );
		return 0;
	}
	// now find the key
	while( fgets( str, 256, fp ) != NULL )  {
		if( strstr( str, key ) )  {
			found = TRUE;
			break;
		}
	}
	fclose( fp );
		
	// exit if key not found
	if( !found )  {
		printf("GetParamString: Key %s not found in file %s\n", key, fileName );
		return 0;
	}
	// remove \n or \r from string	
	if( ( ptr = strchr( str, '\n') ) != NULL )
		*ptr = 0;
	if( ( ptr = strchr( str, '\r') ) != NULL )
		*ptr = 0;
	
	// find the = char
	if( ( ptr = strchr( str, '=' ) ) == NULL )  {
		printf("GetParamString: = not found in key %s\n", key );
		return 0;
	}
	++ptr;					// skip =
	strcpy( to, ptr );
	return TRUE;
}

/* Get the channel file names in the main config (normally winsdr.ini) file */
int GetChannelFileNames()
{
	char str[ 256 ], keyName[ 256 ];
	char path[ 1024 ];	// should really do this dynamically
	char chanpath[ 1024 ];	// should really do this dynamically
	int err;
		
	_snprintf(path, sizeof(path), "%s%s", winSdrPath, wsIniFile);

	// first get the number of channels
	if( !GetParamInt( path, "NumberChannels=", &numberOfChannels ) )
		return 0;
	if( numberOfChannels > MAX_CHANNELS || numberOfChannels < 1 )  {
		printf("GetChannelFileNames: Number of channels error. Should be 1 to %d, is %d\n", 
			MAX_CHANNELS, numberOfChannels );
		return 0;
	}
	if( saveOneChannel == -1 )
		printf("Number of channels: %d\n", numberOfChannels );
	else
		printf("Number of channels: 1\n" );
	
	// now get the channel ini file names
//	printf("Channel ID:\n");
	
	err = 0;
	for( int i = 0; i != numberOfChannels; i++ )  {
		sprintf( keyName, "ChanFile%d=", i+1 );
		if( !GetParamString( path, keyName, channelInfo[i].iniFileName ) )
			return 0;
		
		_snprintf(chanpath, sizeof(path), "%s%s", winSdrPath, channelInfo[i].iniFileName);

		if( !GetParamString( chanpath, "FileExtention=", channelInfo[i].channelName ) )		
			err = 1;

//		printf("%d: Channel ID=%s\n", i+1, channelInfo[i].channelName );
	}		
	if( err )
		return 0;
	else
		return 1;
}

/* Read the channel ini file and parse several fields */
int GetChannelInfo( ChannelInfo *ci )
{
	char path[ 1024 ];	// should really do this dynamically
		
	_snprintf(path, sizeof(path), "%s%s", winSdrPath, ci->iniFileName);

	if( !GetParamInt( path, "AdcBits=", &ci->adcBits ) )  {
		printf("GetChannelInfo: Can't find AdcBits in %s\n", ci->iniFileName );
		return FALSE;
	}
	if( !GetParamDouble( path, "SensorOutVolt=", &ci->sensorVolts ) )  {
		printf("GetChannelInfo: Can't find SensorOutVolt in %s\n", ci->iniFileName );
		return FALSE;
	}
	if( !GetParamDouble( path, "ADInVolt=", &ci->maxInputVolts ) )  {
		printf("GetChannelInfo: Can't find ADInVolt in %s\n", ci->iniFileName );
		return FALSE;
	}
	if( !GetParamDouble( path, "AdcGain=", &ci->ampGain ) )  {
		printf("GetChannelInfo: Can't find AdcGain in %s\n", ci->iniFileName );
		return FALSE;
	}
//	printf("%s: Bits=%d SensorVolts=%g MaxInput=%g Gain=%g\n", ci->iniFileName, 
//		ci->adcBits, ci->sensorVolts, ci->maxInputVolts, ci->ampGain );
	return TRUE;
}

/* Read the main config file and channel ini files for information we need to create the output file */
int ReadIniFiles()
{
	char path[ 1024 ];	// should really do this dynamically
		
	_snprintf(path, sizeof(path), "%s%s", winSdrPath, wsIniFile);

	if( !GetChannelFileNames() )  {		// Read the main config file to get the channels file names
		printf("Error Reading %s file\n", wsIniFile );
		return FALSE;
	}
	// allow command line override of record path
	if(!strlen(recordFilePath)) {		
		if( !GetParamString( path, "RecordPath=", recordFilePath ) )  {
			printf("Error Reading %s file, key RecordPath not found\n", wsIniFile );
			return FALSE;
		}
	}
	if( !GetParamInt( path, "SystemNumber=", &systemNumber ) )  {
		printf("Error Reading %s file, key SystemNumber not found\n", wsIniFile );
		return FALSE;
	}
	for( int i = 0; i != numberOfChannels; i++ )  {
		if( !GetChannelInfo( &channelInfo[i] ) )
			return FALSE;
	}
	
	printf("System Number: %d\n", systemNumber );
	printf("Path To Record Files: %s\n", recordFilePath );
		
	return TRUE;
}

/* Return the time_t time  */
time_t MakeTime( int mon, int day, int year, int hour, int min, int sec )
{
	time_t ret;
	struct tm t;

	t.tm_isdst = -1;
	t.tm_wday = t.tm_yday = 0;
	t.tm_hour = hour;
	t.tm_min = min;
	t.tm_sec = sec;
	t.tm_mday = day;
	t.tm_mon = mon - 1;
	t.tm_year = year - 1900;
	return _mkgmtime(&t);
}

/* Return the time_t time  */
time_t MakeLocalTime( int mon, int day, int year, int hour, int min, int sec )
{
	time_t ret;
	struct tm t;

	t.tm_isdst = -1;
	t.tm_wday = t.tm_yday = 0;
	t.tm_hour = hour;
	t.tm_min = min;
	t.tm_sec = sec;
	t.tm_mday = day;
	t.tm_mon = mon - 1;
	t.tm_year = year - 1900;
	return mktime(&t);
}

/* Display the header block information */
void DisplayHeader( HdrBlock *blk )
{
	char tmStr[40];
	FileInfo *fi;
	int i;
			
	printf("Header Information----\n");
	printf("Number of Channels: %d\n", blk->numChannels);
	printf("Sample Rate: %d\n", blk->sampleRate);
	printf("Data Samples per Block: %d\n", blk->numSamples);
	printf("Number of Data Blocks: %d\n", blk->numBlocks);
	printf("Last Block Size: %d Last Offset %u\n", blk->lastBlockSize, blk->lastBlockOffset);
	MakeTimeStr(blk->startTime, tmStr);
	printf("First Block Start Time: %s\n", tmStr);
	MakeTimeStr(blk->lastTime, tmStr);
	printf("Last Block Start Time: %s\n", tmStr);
	if( blk->fileVersionFlags & HF_SDR24_DATA )		// test for SDR24 data
		printf("Sdr24 Data\n");
	for( i = 0; i != blk->numBlocks; i++ )  {
		fi = &blk->fileInfo[i];
		MakeTimeStr( fi->startTime, tmStr);
		printf("Block=%d Time=%s FilePos=%u Size=%d Julian=%d\n", i+1, tmStr, fi->filePos, 
			fi->blockSize, fi->julianDay );
	}
}

/* Make a time UTC based string */
void MakeTimeStr( time_t ltime, char *str)
{
	struct tm *nt;
	
	nt = gmtime( &ltime );
	sprintf(str, "%02d/%02d/%02d %02d:%02d:%02d", nt->tm_mon+1, nt->tm_mday, 
		nt->tm_year % 100, nt->tm_hour, nt->tm_min, nt->tm_sec);
}

/* Make a time UTC based string including milliseconds */
void MakeTimeStrMs( char *str, time_t ltime, int tick )
{
	struct tm *nt;
	int ms = tick % 1000;
	
	nt = gmtime( &ltime );
	sprintf(str, "%02d/%02d/%02d %02d:%02d:%02d.%03d", nt->tm_mon+1, nt->tm_mday, 
		nt->tm_year % 100, nt->tm_hour, nt->tm_min, nt->tm_sec, ms );
}

/* Normalize the 32 bit data to the user data array */
void NormalizeSdrData( int *data, BYTE *dataBlk )
{
	int iData, cnt = hdrBlock.numSamples * 60;
	BYTE *dPtr = (BYTE *)dataBlk + sizeof(InfoBlockNew), *iPtr = (BYTE *)&iData;
		
	/* the following converts the raw A/D data into a intel format 32 bit int */
	while( cnt-- )  {
		if( *dPtr & 0x80 )
			iPtr[3] = 0xff;
		else
			iPtr[3] = 0;
		iPtr[2] = *dPtr++;
		iPtr[1] = *dPtr++;
		iPtr[0] = *dPtr++;
		*data++ = iData;
	}
}

/* Decompress the data into the short data *data.  */
void DecompressBuffer(short *data, BYTE *dataBlk, int charOrShortLen)
{
	int mask = 1, cnt = hdrBlock.numSamples * 60, bitCount = 0;
	InfoBlockNew *infoBlk;
	BYTE *cos;				// char or short flag pointer
	char *ptr;
		
	// Set the infoBlk pointer to the begining of the block
	infoBlk = (InfoBlockNew *)dataBlk;
	
	// Set the char or short flag pointer right after the info block
	cos = dataBlk + sizeof(InfoBlockNew);
	
	// Set ptr to the beginning of the A/D data
	ptr = (char *)dataBlk + sizeof(InfoBlockNew) + charOrShortLen;
	
	/* Now decompress one minutes worth of data */
	while(cnt--)  {
		if(*cos & mask)  {				// check for a short sample
			*data++ = *((short *)ptr);	// save the sample 
			ptr += 2;					// point to the next sample
		}
		else							// not a short must be char
			*data++ = *ptr++;			// save the sample
		if(++bitCount >= 8)  {			// next bit
			bitCount = 0;
			mask = 1;
			++cos;
		}
		else
			mask <<= 1;
	}
}
		
/* Unblock the 16 bit data to the user data array */
void Unblock16BitData( InfoBlockNew *blk, short *inData )
{
	int s, c, idx, cnt;
	short sample;
		
	idx = 0;
	for( s = 0; s != 60; s++ )  {
		cnt = hdrBlock.sampleRate;
		while(cnt--)  {
			for( c = 0; c != hdrBlock.numChannels; c++ )  {
				sample = *inData++;
				if( ( SaveSample( blk, c, (int)sample ) ) == 0 )
					return;
			}
			++idx;
			sampleTmAcc += sampleDelta;
		}
	}	
}

/* Unblock the 32 bit data to the user data array */
void Unblock24BitData( InfoBlockNew *blk, int *inData )
{
	int s, c, idx, cnt;
		
	idx = 0;
	for(s = 0; s != 60; s++)  {
		cnt = hdrBlock.sampleRate;
		while(cnt--)  {
			for(c = 0; c != hdrBlock.numChannels; c++)  {
				if( ( SaveSample( blk, c, *inData++ ) ) == 0 )
					return;
			}
			++idx;
			sampleTmAcc += sampleDelta;
		}
	}	
}

/* Calculate the one minute start buffer time */
double CalcMsTime( time_t ltime, int tick )
{
	return (double)ltime + ( (double)( tick % 1000 ) / 1000.0 );
}

/* Make a time UTC based string including milliseconds */
void MakeTimeStrDouble( char *str, double tm )
{
	struct tm *nt;
	double ms, lt;
	time_t ltime;
	
	ms = modf( tm, &lt );
	ltime = (time_t)lt;
	nt = gmtime( &ltime );
	sprintf(str, "%02d/%02d/%02d %02d:%02d:%02d.%03d", nt->tm_mon+1, nt->tm_mday, 
		nt->tm_year % 100, nt->tm_hour, nt->tm_min, nt->tm_sec, (int)( (  ms * 1000.0 ) + .0005 ) );
}

void MakeOffsetStr( char *str, double tm )
{
	sprintf(str, "%.3f", tm );
}

/* Make a time UTC based string for the PSN Text Header format */
void MakeTimeStrPsn( char *str, double tm )
{
	struct tm *nt;
	double ms, lt;
	time_t ltime;
	
	ms = modf( tm, &lt );
	ltime = (time_t)lt;
	nt = gmtime( &ltime );
	sprintf(str, "%04d/%02d/%02d %02d:%02d:%02d.%03d", nt->tm_year + 1900, nt->tm_mon+1, nt->tm_mday, 
		nt->tm_hour, nt->tm_min, nt->tm_sec, (int)( (  ms * 1000.0 ) + .0005 ) );
}
