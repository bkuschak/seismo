/* drf2txt.cpp - Save data from a winsdr daily record file to a text file
*
* 08/28/15 Version 1.3 - Added PGA Gain to the header output section 
* 11/16/16 Version 1.4 - Fixed problem with working with VolksMeter data files
*
*/

#include "drf2txt.h"

#if !defined(_WIN32) && !defined(_WIN64)
/* Use POSIX function */
#define stricmp 	strcasecmp
#define _snprintf	snprintf
#endif

/* Data from the channel ini files */
ChannelInfo channelInfo[ MAX_CHANNELS ];
int numberOfChannels;

/* Data from the winsdr.ini file */
char recordFilePath[ 256 ];
char winSdrPath[ 256 ];
int systemNumber;

/* User input data */
time_t userStartTime;
double dStartTime;
int minutesToSave, samplesToSave, savedSamples;
char saveChannel[ 128 ];
int saveOneChannel = -1;
int saveSampleTime = 0;
int useSecondsFromEpoch = 0;

/* Current input file info */
FILE *inFp;
time_t currentFileTime;
FileInfo *finfo;
ULONG fpos;

/* Record file header block */
HdrBlock hdrBlock;
BYTE *dataBlk;

/* Saving data flag */
int savingDataFlag;

FILE *outFp = NULL;
char outFileName[ 256 ];

/* Main config file to use. Default is winsdr.ini */
char wsIniFile[ 256 ];

double dataAvg[ MAX_CHANNELS ];
int dataAvgCount[ MAX_CHANNELS], saveNth = 1;

int totalSaved = 0, skipSamples;
int fullHeader = 0, dispHeader = 0, psnTextHeader = 0, useLocalTime = 0, noHeader = 0;
int debug = 0;

double sampleDelta;			// 1.0 / sample_rate
double firstSampleTime;

double sampleTmAcc;
double epochOffset;			// seconds from the epoch

const char *separator = ",";		// comma separated values by default

int SaveSample( InfoBlockNew *blk, int channel, int data )
{
	double ddata;
	char tmStr[ 64 ];
		
	if( skipSamples )  {
		--skipSamples;
		return 1;
	}
		
	if( !samplesToSave )
		return 0;
		
	if( !savingDataFlag )  {
		savingDataFlag = TRUE;
		printf("Start Saving Data to %s\n", outFileName );
		firstSampleTime = userStartTime;
		MakeTimeStrDouble( tmStr, firstSampleTime );
		//sampleTmAcc = 0;
		sampleTmAcc = epochOffset;		/* may be zero */
		if( !noHeader )
			SaveHeader( blk, channel );
	}
		
	// check to see if the user is only saving one channel
	if( saveOneChannel != -1 )  {
		if( channel == saveOneChannel )  {
			if( saveNth == 1 )  {
				if( saveSampleTime )
					fprintf( outFp, "%.3f%s", sampleTmAcc, separator );
				fprintf( outFp, "%d\n", data );
				++totalSaved;
				if( samplesToSave )
					--samplesToSave;
			}
			else  {
				// down sample the data by averaging samples
				dataAvg[ channel ] += (double)data;
				if( ++dataAvgCount[ channel ] >= saveNth )  {
					ddata = dataAvg[ channel ] / (double)dataAvgCount[ channel ];
					if( saveSampleTime )
						fprintf( outFp, "%.3f%s", sampleTmAcc, separator );
					fprintf( outFp, "%g\n", ddata );
					dataAvgCount[ channel ] = 0;
					dataAvg[ channel ] = 0.0;
					++totalSaved;
					if( samplesToSave )
						--samplesToSave;
				}
			}
		}
		return 1;	
	}
	
	if( saveNth == 1 )  {
		if( saveSampleTime && !channel )
			fprintf( outFp, "%.3f%s", sampleTmAcc, separator );
		if( channel == (numberOfChannels-1) )
			fprintf( outFp, "%d\n", data );
		else
			fprintf( outFp, "%d%s", data, separator );
		++totalSaved;
		if( samplesToSave )
			--samplesToSave;
		return 1;
	}
	
	dataAvg[ channel ] += (double)data;
	if( ++dataAvgCount[ channel ] >= saveNth )  {
		ddata = dataAvg[ channel ] / (double)dataAvgCount[ channel ];
		if( saveSampleTime && !channel )
			fprintf( outFp, "%.3f%s", sampleTmAcc, separator );
		if( channel == (numberOfChannels-1) )
			fprintf( outFp, "%g\n", ddata );
		else
			fprintf( outFp, "%g%s", ddata, separator );
		dataAvgCount[ channel ] = 0;
		dataAvg[ channel ] = 0.0;	
		++totalSaved;
		if( samplesToSave )
			--samplesToSave;
	}
	return 1;
}

int SaveHeader( InfoBlockNew *blk, int channel )
{
	char tmStr[ 64 ];
	ChannelInfo *ci;
	double v;
			
	if( psnTextHeader )  {
		MakeTimeStrPsn( tmStr, firstSampleTime );
		fprintf( outFp, "! PSN ASCII Event File Format 2.0\n");
		fprintf( outFp, "Start Time: %s\n", tmStr );
		fprintf( outFp, "Number of Samples: %d\n",  savedSamples );
		fprintf( outFp, "SPS: %g\n", (double)hdrBlock.sampleRate / (double)saveNth );
		fprintf( outFp, "A/D Converter Bits: %d\n", channelInfo[ channel ].adcBits );
		fprintf( outFp, "PGA Gain: %g\n", channelInfo[ channel ].ampGain );
		fprintf( outFp, "Data:\n" );
	}
	else  {	
		MakeTimeStrDouble( tmStr, firstSampleTime );
		fprintf( outFp, "Start Time: %s\n", tmStr );
		fprintf( outFp, "Sample Rate: %g\n", (double)hdrBlock.sampleRate / (double)saveNth );
	
		if( saveOneChannel == -1 )
			fprintf( outFp, "Number of Channels: %d\n", numberOfChannels );
		else  {
			printf("Saving Channel: %s\n", channelInfo[ saveOneChannel ].channelName );
			fprintf( outFp, "Number of Channels: 1\n" );
		}	
		
		if( fullHeader )  {
			for( int c = 0; c != numberOfChannels; c++ )  {
				ci = &channelInfo[ c ];
				if( ci->maxInputVolts && ci->adcBits )  {
					v =  ci->maxInputVolts / ((double)pow( 2.0, (double)ci->adcBits ) / 2.0);		
				}
				else  {
					v = 0.0;		
				}
				fprintf( outFp, "Ch%d Volts Per Count: %.12f\n", c+1, v );
			}
		}
		
		fprintf( outFp, "Data Samples Per Channel: %d\n", ( minutesToSave * 60 * hdrBlock.sampleRate ) / saveNth );
	}
	
	return TRUE;
}

/* Try and find the start time within the record file */
int FindStartTime( int *index )
{
	FileInfo *finfo;
	time_t diff;
		
	for( int i = *index; i != hdrBlock.numBlocks; i++ )  {
		finfo = &hdrBlock.fileInfo[ i ];
		diff = userStartTime - finfo->startTime;
		if( !i && diff < 0 )
			return -1;			// return start time not in this file
		if( finfo->startTime && abs( (int)diff ) <= 60 )  {
			if( i )				// go back one block
				--i;
			*index = i;
			return 1;			// found
		}
	}
	return 0;					// not found
}

/* Used to open the next record file if spanning more then one day */
int OpenNextRecordFile()
{
	char fileName[ 256 ];
	struct tm *nt;
	int sts;
		
	// close the current file
	if( inFp )  {
		fclose( inFp );
		inFp = 0;
	}
	
	currentFileTime += (24 * 60 * 60 );		// next day	
	
	nt = gmtime( &currentFileTime );
	sprintf( fileName, "%ssys%d.%04d%02d%02d.dat", recordFilePath, 
		systemNumber, nt->tm_year+1900, nt->tm_mon+1, nt->tm_mday );
	
	printf("Open Next Record File %s\n", fileName );
	
	/* Try to open the record file */
	if( ( inFp = fopen( fileName, "rb" ) ) == NULL )  {
		printf("Can't open next record file %s\n", fileName );
		return 0;
	}
		
	/* Read in the header block */
	if( ( sts = fread( &hdrBlock, 1, sizeof( hdrBlock ), inFp ) ) != sizeof( hdrBlock ) )  {
		printf("Header Read Error\n");
		if( inFp )  {
			fclose( inFp );
			inFp = 0;
		}
		return 0;
	}
	
	finfo = &hdrBlock.fileInfo[0];

   	// we should be at the correct file position
   	fpos = ftell( inFp );
		
	if((sts = fread( dataBlk, 1, sizeof(InfoBlockNew ), inFp)) != sizeof(InfoBlockNew))  {
		if( inFp )  {
			fclose( inFp );
			inFp = 0;
		}
		return 0;
	}

	return 1;
}

/* Used to open the previous record file if the start time is not found in the first record file */
int OpenPrevRecordFile()
{
	char fileName[ 256 ];
	struct tm *nt;
	int sts;
		
	// close the current file
	if( inFp )  {
		fclose( inFp );
		inFp = 0;
	}
	
	currentFileTime -= (24 * 60 );		// next day	
	
	nt = gmtime( &currentFileTime );
	sprintf( fileName, "%ssys%d.%04d%02d%02d.dat", recordFilePath, 
		systemNumber, nt->tm_year+1900, nt->tm_mon+1, nt->tm_mday );
	
	printf("Open Previous File %s\n", fileName );
	
	/* Try to open the record file */
	if( ( inFp = fopen( fileName, "rb" ) ) == NULL )  {
		printf("Can't open previous record file %s\n", fileName );
		return 0;
	}
		
	/* Read in the header block */
	if( ( sts = fread( &hdrBlock, 1, sizeof( hdrBlock ), inFp ) ) != sizeof( hdrBlock ) )  {
		printf("Header Read Error\n");
		if( inFp )  {
			fclose( inFp );
			inFp = 0;
		}
		return 0;
	}
	
	return 1;
}

/* Now make the output file */
void MakeOutputFile()
{
	char fileName[ 256 ], sStr[ 64 ], eStr[ 64 ], dStr[ 64 ], tmStr[ 64 ];
	struct tm *nt;
	short *tmpData;			// holds 16 bit data
	int *tmp24Data;		// holds 32 bit VolksMeter/SDR24 data
	InfoBlockNew *blk;
	int size, sts, charOrShortLen, index = 0, findStart = 1;
	double start, end, diff;
				
	//sampleTmAcc = 0.0;
	sampleTmAcc = epochOffset;		/* may be zero */
	savingDataFlag = 0;
	memset( dataAvg, 0, sizeof( dataAvg ) );
	memset( dataAvgCount, 0, sizeof( dataAvgCount ) );
	
	currentFileTime = userStartTime;
	
	/* First make the record file name */
	nt = gmtime( &currentFileTime );
	sprintf( fileName, "%ssys%d.%04d%02d%02d.dat", recordFilePath, 
		systemNumber, nt->tm_year+1900, nt->tm_mon+1, nt->tm_mday );
		
	/* And now the output file name */
	if( !outFileName[0] )
		sprintf( outFileName, "%02d%02d%02d_%02d%02d%02d.txt", nt->tm_mon+1, nt->tm_mday, nt->tm_year % 100, 
			nt->tm_hour, nt->tm_min, nt->tm_sec );
	
	/* Try to open the output file */
	if( ( outFp = fopen( outFileName, "w" ) ) == NULL )  {
		printf("Can't open output file %s\n", outFileName );
		return;
	}
	
	/* Try to open the record file */
	if( ( inFp = fopen( fileName, "rb" ) ) == NULL )  {
		printf("Can't open daily record file %s\n", fileName );
		return;
	}
	
	/* Read in the header block */
	if( ( sts = fread( &hdrBlock, 1, sizeof( hdrBlock ), inFp ) ) != sizeof( hdrBlock ) )  {
		printf("Header Read Error\n");
		if( inFp )  {
			fclose( inFp );
			inFp = 0;
		}
		return;
	}
	sampleDelta = 1.0 / (double)hdrBlock.sampleRate;		
		
	if( numberOfChannels != hdrBlock.numChannels )  {
		printf("Number of channels in %s (%d) does not match number of channels in record file (%d)\n", 
			wsIniFile, numberOfChannels, hdrBlock.numChannels );
		if( inFp )  {
			fclose( inFp );
			inFp = 0;
		}
		return;
	}
	
	/* Display the information in the header */
	if( dispHeader )  {
		DisplayHeader( &hdrBlock );
		fclose( inFp );
		inFp = 0;
		return;
	}
	
	if( ( sts = FindStartTime( &index ) ) == 0 )  {
		printf("Can't Find Start Time in Record File\n");
		return;
	}
	if( sts == -1 )  {			// indicates start time not found in first minute block
		index = 0;
		if( !OpenPrevRecordFile() )
			return;
		if( ( sts = FindStartTime( &index ) ) <= 0 )  {
			printf("Can't find start time in previous record file\n");
			return;
		}
	}
	
	/* 16 Bit data only - Each data block has an array of flags to tell the unpacker if the sample is 
	    stored as a 8 bit character (+-127) or a short (+- 32K). This calculates
	    the the size of the array. WinSDR saves this array right after the InfoBlock
		and before the compressed data */
	charOrShortLen = ((hdrBlock.numSamples * 60) / 8) + 1;
	
	/* Create a buffer large enough to hold one block of data */
	/* First test for SDR24 or VoltsMeter data */
	if( ( hdrBlock.fileVersionFlags & HF_SDR24_DATA ) || ( hdrBlock.fileVersionFlags & HF_VM_DATA ) )  {
		if(!(dataBlk = (BYTE *)malloc((sizeof(int) * 60 * hdrBlock.numSamples) + sizeof(InfoBlockNew))))  {
			printf("Out of memory!\n");
			if( inFp )  {
				fclose( inFp );
				inFp = 0;
			}
			return;
		}
	}
	else  {
		if(!(dataBlk = (BYTE *)malloc((sizeof(short) * 60 * hdrBlock.numSamples) + 
				charOrShortLen + sizeof(InfoBlockNew))))  {
			printf("Out of memory!\n");
			if( inFp )  {
				fclose( inFp );
				inFp = 0;
			}
			return;
		}
	}	
	
	blk = (InfoBlockNew *)dataBlk;		// Set pointer to the beginning of the block
		
	/* Create a buffer to hold the decompressed data.  HdrBlock.numSamples is in 
	   samples per second, so the 60 is to make the buffer large enough to hold
	   one minutes worth of data. */
	/* First test for SDR24 or VoltsMeter data */
	if( ( hdrBlock.fileVersionFlags & HF_SDR24_DATA ) || ( hdrBlock.fileVersionFlags & HF_VM_DATA ) )  {
		if(!(tmp24Data = (int *)malloc(sizeof(int) * 60 * hdrBlock.numSamples)))  {
			printf("Out of memory!\n");
			free(dataBlk);
			if( inFp )  {
				fclose( inFp );
				inFp = 0;
			}
			return;
		}
	}
	else  {
		if(!(tmpData = (short *)malloc(sizeof(short) * 60 * hdrBlock.numSamples)))  {
			printf("Out of memory!\n");
			free(dataBlk);
			if( inFp )  {
				fclose( inFp );
				inFp = 0;
			}
			return;
		}
	}
	
	fseek( inFp, hdrBlock.fileInfo[index].filePos, SEEK_SET);
	
	/* Now go through the file and read each data block */
	while(TRUE)  {
		
		finfo = &hdrBlock.fileInfo[index];

      	// we should be at the correct file position
      	fpos = ftell( inFp );
		
		/* First read in the InfoBlock part of the data block */
		if((sts = fread( dataBlk, 1, sizeof(InfoBlockNew ), inFp)) != sizeof(InfoBlockNew))  {
			if( ! OpenNextRecordFile() )  {
				printf("End of File\n");
				break;
			}
			else  {
				index = 0;
			}
		}
		/* Check for a good block ID */
 		if(blk->goodID != GOOD_BLK_ID)  {
			printf("Bad Header Check ID\n");
			break;
		}

		if( fpos != finfo->filePos )  {
        	printf("Incorrect file position! Should be here: %u but instead are here: %u\n", 
				finfo->filePos, fpos);
			break;
		}
      	++index;
		
		// calculate the start and end times of this one minute block of data
		start = CalcMsTime( blk->startTime, blk->startTimeTick );
		end = ( start + 60.0 ) - sampleDelta; 
		
		if( debug )  {
			MakeTimeStrMs( tmStr, blk->startTime, blk->startTimeTick );	
			printf("block=%s\n", tmStr );
		}
					
		if( findStart )  {
			if( dStartTime >= start && dStartTime <= end )  {
				double d = dStartTime - start;
				skipSamples = (int)( d / sampleDelta ) * numberOfChannels;
				if( saveOneChannel != -1 )
					savedSamples = samplesToSave = minutesToSave * 60 * hdrBlock.sampleRate;
				else
					savedSamples = samplesToSave = minutesToSave * 60 * hdrBlock.sampleRate * numberOfChannels;
				samplesToSave /= saveNth;
				savedSamples /= saveNth;
				if( debug )  {
					MakeTimeStrDouble( dStr, dStartTime );
					MakeTimeStrDouble( sStr, start );
					MakeTimeStrDouble( eStr, end );
					printf("StartTime=%s Block Start=%s End=%s\n", dStr, sStr, eStr );	
					printf("Start Block diff=%f skip=%d saving=%d\n", d, skipSamples, samplesToSave );
				}
				findStart = 0;
			}
		}
		
		/* Calculate the data part of the block */
		size = blk->blockSize - sizeof(InfoBlockNew);
		
		/* Read in the rest of the block of data*/
		if((sts = fread(&dataBlk[sizeof(InfoBlockNew)], 1, size, inFp)) != size)  {
			printf("Read Error\n");
			break;
		}
	
		if( findStart )			// keep reading until start found
			continue;
			
		/* Now unblock the data. Unblockers call SaveSample() above for each sample */
		/* First test for SDR24 or VolksMeter data */
		if( ( hdrBlock.fileVersionFlags & HF_SDR24_DATA ) || ( hdrBlock.fileVersionFlags & HF_VM_DATA ) )	{
			/* Decompress 24 bit data block into tmp24Data */
			NormalizeSdrData( tmp24Data, dataBlk );
			
			/* Unblock data and save it to the output file */
			Unblock24BitData( blk, tmp24Data );
		}
		else  {
			/* Decompress 16 bit data block into tmpData */
			DecompressBuffer(tmpData, dataBlk, charOrShortLen);

			/* Unblock data and save it to the output file */
			Unblock16BitData( blk, tmpData );
		}
		
		/* See if we are saving the data. Stop when done. */
		if( savingDataFlag && !samplesToSave )
			break;
	}
	
	if( !dispHeader )
		printf("Done Saving Data - Total Samples Saved = %d\n", totalSaved );
	
	/* Done reading the file. Now do some clean up. */
	free(dataBlk);
	
	/* test for VolksMeter or Sdr24 data */
	if( ( hdrBlock.fileVersionFlags & HF_SDR24_DATA ) || ( hdrBlock.fileVersionFlags & HF_VM_DATA ) )
		free(tmp24Data);
	else
		free(tmpData);
	
	if( outFp )
		fclose( outFp );
		
	if( inFp )  {
		fclose( inFp );
		inFp = 0;
	}
}

void PrintUsage()
{
	printf( "Usage: drf2txt [options] start_time minutes_to_save.\n" ); 
	printf( "       Start time format = mmdd_hhmm or mmddyy_hhmm\n" );
	printf( "       Options:         Must be before start time and minutes to save\n" );
	printf( "        -o outfile      Used to specify an output file\n" );
	printf( "        -d n            Down sample data by a facter of n\n" );
	printf( "        -c channel_id   Specify channel to save\n" );
	printf( "        -w iniFile      Main config file to read in. Default is winsdr.ini\n");
	printf( "        -h              Dump record file header\n" );
	printf( "        -f              Save more header information in the output file\n" );
	printf( "        -p              Save header in PSN Text File format\n" );
	printf( "        -l              Start time is local time not UTC time\n" );
	printf( "        -n              No header information\n" );
	printf( "        -v              Display program version number\n" );
	printf( "        -t              Add sample time offset to output file\n" );
	printf( "        -T              Add sample time (UNIX time) to output file\n" );
	printf( "        -s              Use space-separated instead of comma-separated values\n" );
	printf( "        -P              Override path to WinSDR root directory\n" );
	printf( "        -R              Override path to WinSDR daily record file directory\n" );
}

int main( int argc, char *argv[] )
{
	int argIdx = 1, found = 0, i;
	
	saveChannel[ 0 ] = outFileName[ 0 ] = wsIniFile[ 0 ] = 0;
	
	--argc;					// skip first arg
	
	if( argc == 1 && !strcmp( argv[ 1 ], "-v") )  {
		printf("Version: %s\n", VERSION );
		exit( 0 );
	}
	
	if( argc < 2 )  {		// need two or more args
		PrintUsage();
		exit( 1 );
	}
		
	while( argc > 2 )  {
		if( !strcmp( argv[ argIdx ], "-c") )  {
			if( argc )
				--argc;
			++argIdx;
			if( argc )  {
				strcpy( saveChannel, argv[ argIdx++ ] );
				if( argc )
					--argc;
			}
			continue;
		}
		else if( !strcmp( argv[ argIdx ], "-d") )  {
			if( argc )
				--argc;
			++argIdx;
			if( argc )  {
				saveNth = atoi( argv[ argIdx++ ] );
				if( saveNth < 1 || saveNth > 1000000 )  {
					printf("Downsample input value error\n");
					PrintUsage();
					exit( 1 );
				}
				--argc;
			}
			continue;
		}
		else if( !strcmp( argv[ argIdx ], "-o") )  {
			if( argc )
				--argc;
			++argIdx;
			if( argc )  {
				strcpy( outFileName, argv[ argIdx++ ] );
				--argc;
			}
			continue;
		}
		else if( !strcmp( argv[ argIdx ], "-w") )  {
			if( argc )
				--argc;
			++argIdx;
			if( argc )  {
				strcpy( wsIniFile, argv[ argIdx++ ] );
				printf("Using wsIniFile: %s\n", wsIniFile);
				--argc;
			}
			continue;
		}
		else if( !strcmp( argv[ argIdx ], "-f") )  {
			if( argc )
				--argc;
			++argIdx;
			fullHeader = 1;			
		}
		else if( !strcmp( argv[ argIdx ], "-h") )  {
			if( argc )
				--argc;
			++argIdx;
			dispHeader = 1;			
		}
		else if( !strcmp( argv[ argIdx ], "-p") )  {
			if( argc )
				--argc;
			++argIdx;
			psnTextHeader = 1;			
		}
		else if( !strcmp( argv[ argIdx ], "-l") )  {
			if( argc )
				--argc;
			++argIdx;
			useLocalTime = 1;			
		}
		else if( !strcmp( argv[ argIdx ], "-n") )  {
			if( argc )
				--argc;
			++argIdx;
			noHeader = 1;			
		}
		else if( !strcmp( argv[ argIdx ], "-t") )  {
			if( argc )
				--argc;
			++argIdx;
			saveSampleTime = 1;			
		}
		else if( !strcmp( argv[ argIdx ], "-T") )  {
			if( argc )
				--argc;
			++argIdx;
			saveSampleTime = 1;			
			useSecondsFromEpoch = 1;			
		}
		else if( !strcmp( argv[ argIdx ], "-s") )  {
			if( argc )
				--argc;
			++argIdx;
			separator = " ";
		}
		else if( !strcmp( argv[ argIdx ], "-P") )  {
			if( argc )
				--argc;
			++argIdx;
			if( argc )  {
				// ensure trailing slash
				_snprintf( winSdrPath, sizeof(winSdrPath), "%s/", argv[ argIdx++ ] );
				printf("Using WinSDR path: %s\n", winSdrPath);
				--argc;
			}
		}
		else if( !strcmp( argv[ argIdx ], "-R") )  {
			if( argc )
				--argc;
			++argIdx;
			if( argc )  {
				// ensure trailing slash
				_snprintf( recordFilePath, sizeof(recordFilePath), "%s/", argv[ argIdx++ ] );
				printf("Using Record File Path: %s\n", recordFilePath);
				--argc;
			}
			continue;
		}
	}
	
	// use the default config file winsdr.ini if not specifed
	if( !wsIniFile[ 0 ] )
		strcpy( wsIniFile, "winsdr.ini" );
	
	if( !ReadIniFiles() )
		exit( 1 );
	
	// find the channel ID if user is saving one channel
	if( strlen( saveChannel ) )  {
		for( i = 0; i != numberOfChannels; i++ )  {
			if( !stricmp( channelInfo[i].channelName, saveChannel ) )  {
				found = 1;
				saveOneChannel = i;
			}
		}
		if( !found )  {
			printf("Channel to save [%s] not found in ini files\n", saveChannel );
			PrintUsage();
			exit( 1 );
		}
	}
	else if( psnTextHeader )  {
		printf("You must specify one channel using the -c option when saving data in the PSN Text file format\n");
		exit( 1 );
	}
		
	if( psnTextHeader && saveSampleTime )  {
		printf("You can not specify the  -t option when saving data in the PSN Text file format\n");
		exit( 1 );
	}	
		
	if( !dispHeader && argc != 2 )  {
		printf("Input Argument Error\n");
		PrintUsage();
		exit( 1 );
	}
		
	if( ! ( userStartTime = ParseStartTime( argv[ argIdx++ ] ) ) )  {
		printf("Start time input error\n");
		PrintUsage();
		exit( 1 );
	}
	dStartTime = (double)userStartTime;

	if(useSecondsFromEpoch)
		epochOffset = dStartTime;
	else
		epochOffset = 0;
	
	if( !dispHeader )
		minutesToSave = atoi( argv[ argIdx ] );
	
	MakeOutputFile();
	
	exit( 0 );
	return 0;	/* suppress warning */
}
