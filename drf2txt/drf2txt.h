/* drf2txt.h - Save data from a winsdr daily record file to a text file */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>
#include <math.h>

#if !defined(_WIN32) && !defined(_WIN64)
#include <stdint.h>
#define UINT64					uint64_t		// 64 bits
#define INT64					int64_t			// 64 bits
#define ULONG					uint32_t		// 32 bits
#define UINT					uint32_t		// 32 bits
#define WORD					uint16_t		// 16 bits
#define BYTE					uint8_t			// 8 bits
#else
#define UINT64					unsigned long long	// 64 bits
#define INT64					long long			// 64 bits
#define ULONG					unsigned long		// 32 bits
#define UINT					unsigned int		// 32 bits
#define WORD					unsigned short		// 16 bits
#define BYTE					unsigned char		// 8 bits
#endif
#define TRUE					1
#define FALSE					0

#define MAX_FILE_INFO			2000		// set some maximums
#define MAX_CHANNELS			12
#define MAX_USER_LEN			(200*60)	// Maximum user data buffer size for each channel 
	
#define GOOD_BLK_ID				0xa55a		// Each data block has this at the beginning of block

// Header Flags
#define HF_SDR24_DATA			0x2000000	// This bit will be set if SDR24 data
#define HF_VM_DATA				0x4000000	// This bit will be set if VolksMeter data
	
#define VERSION					"1.4"

// Holds the channel information from the ini config files
typedef struct  {
	char iniFileName[ 64 ];
	char channelName[ 64 ];
	int adcBits;
	double sensorVolts;
	double maxInputVolts;
	double ampGain;
} ChannelInfo;

#pragma pack(1)
	
/* Record file structures */
typedef struct  {
	ULONG startTime, filePos;
	int blockSize, julianDay;
} FileInfo;

/* First part of the record file */
typedef struct  {
	UINT fileVersionFlags;
	int	sampleRate,
		numSamples,
		numChannels,
		numBlocks,
		lastBlockSize;
	ULONG startTime, lastTime,
		 lastBlockOffset;
	FileInfo fileInfo[MAX_FILE_INFO];
} HdrBlock;
	
/* One minute buffer information */
typedef struct  {
	WORD goodID, flags;
	UINT64 alarmBits;
	ULONG startTime,
		 startTimeTick,
		 blockSize;
} InfoBlockNew;

#pragma pack()

time_t ParseStartTime( char *inStr );
time_t MakeTime( int mon, int day, int year, int hour, int min, int sec );
time_t MakeLocalTime( int mon, int day, int year, int hour, int min, int sec );
int ReadIniFiles();
void DisplayHeader( HdrBlock *blk );
void MakeTimeStr( time_t ltime, char *str );
void MakeTimeStrMs( char *str, time_t ltime, int tick );
void NormalizeSdrData( int *data, BYTE *dataBlk );
void Unblock24BitData( InfoBlockNew *blk, int *inData );
void DecompressBuffer(short *data, BYTE *dataBlk, int charOrShortLen);
void Unblock16BitData( InfoBlockNew *blk, short *inData );
int SaveSample( InfoBlockNew *blk, int channel, int data );
double CalcMsTime( time_t ltime, int tick );
void MakeTimeStrDouble( char *str, double tm );
int SaveHeader( InfoBlockNew *blk, int channel );
void MakeTimeStrPsn( char *str, double tm );
void MakeOffsetStr( char *str, double tm );
