/* $Id: platform.h 4494 2011-08-09 07:38:18Z paulf $ */
/*---------------------------------------------------------------------
  
	Platform include.

    Copyright (c) 2000-2007 - DAQ Systems, LLC. - All rights reserved.

-----------------------------------------------------------------------*/
#if !defined _PLATFORM_H_INCLUDED
#define _PLATFORM_H_INCLUDED

/* Platform: must be SOLARIS, LINUX, WIN32, or DOS */

#if defined (_SOLARIS)
#   if !defined (SOLARIS)
#       define SOLARIS
#   endif
#endif

#if defined (_WIN32)
#   if !defined (WIN32)
#       define WIN32
#   endif
#endif

#if defined (_LINUX)
#   if !defined (LINUX)
#       define LINUX
#   endif
#endif

#if defined (_MACOSX)
#   if !defined (MACOSX)
#       define MACOSX
#   endif
#endif

#if defined (_DOS) || defined(DOS)
#   if !defined (DOS16)
#       define DOS16
#   endif
#endif

#if !defined (SOLARIS) && !defined (WIN32) && !defined (LINUX) && !defined (DOS) && !defined(MACOSX)
#   error Platform not defined!
#endif

/* Common C runtime includes... */
#include <stdio.h>
#include <ctype.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stddef.h>
#include <errno.h>
#include <signal.h>
#include <math.h>

/* Solaris ------------------------------------------------------------*/
#if defined (SOLARIS)

#include <unistd.h>

#   define VOID_SIZE 0xFFFFFFFF
#   define CLOCK_DIVIDER 1000
#	define MAX_PATH_LEN	255

#   if defined (i386)
#       define X86_UNIX32
#   elif defined (sparc)
#       define SPARC_UNIX32
#   endif
#endif										/* SOLARIS */

/* Linux --------------------------------------------------------------*/
#if defined (LINUX) || defined (MACOSX)

#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#   define VOID_SIZE 0xFFFFFFFF
#   define CLOCK_DIVIDER 1000
#	define MAX_PATH_LEN	255
#	define HAVE_SYSLOG

#   if defined (i386)
#       define X86_UNIX32
#   elif defined (sparc)
#       define SPARC_UNIX32
#   endif
#endif										/* LINUX */

/* Windows 32 bit -----------------------------------------------------*/

#if defined (WIN32)

#include <windows.h>
#include <process.h>

/* Thread sleep function, Sleep() arg is milliseconds */
#   define sleep(seconds) (Sleep( (DWORD)((seconds) * 1000) ))

#   define __VERSION__ "MSC-6.0"

#   define VOID_SIZE 0xFFFFFFFF
#   define CLOCK_DIVIDER 1
#   define MAX_PATH_LEN	255

#   define X86_WIN32

#   define vsnprintf _vsnprintf
#   define snprintf _snprintf
#   define strcasecmp stricmp
#   define strncasecmp strnicmp
#endif										/* WIN32 */

/* DOS will never die -------------------------------------------------*/

#if defined (DOS16)

#   define VOID_SIZE 0xFFFF
#   define CLOCK_DIVIDER 1

#   define X86_16BIT
#endif										/* DOS */

/* Portable data types key off the platform type defined above --------*/

//#include "stdtypes.h"

/* Compile time discovery of host byte order (additions welcome) ------*/

#if defined(X86_16BIT) || defined(X86_WIN32) || defined(X86_UNIX32)
#   if !defined LITTLE_ENDIAN_HOST
#       define LITTLE_ENDIAN_HOST
#   endif
#elif defined(SPARC_UNIX32)
#   if !defined BIG_ENDIAN_HOST
#       define BIG_ENDIAN_HOST
#   endif
#endif

/* Macros for mutual exclusion portability ----------------------------*/
#if defined (LINUX) || defined (SOLARIS)
#   include <pthread.h>
typedef pthread_mutex_t MUTEX;

#   define MUTEX_LOCK(arg)      pthread_mutex_lock(arg)
#   define MUTEX_TRYLOCK(arg)   (pthread_mutex_trylock(arg) == 0 ? TRUE : FALSE)
#   define MUTEX_UNLOCK(arg)    pthread_mutex_unlock(arg)
#   define MUTEX_INIT(arg)      pthread_mutex_init((arg), NULL)
#   define MUTEX_DESTROY(arg)   pthread_mutex_destroy(arg);
#   define MUTEX_INITIALIZER    PTHREAD_MUTEX_INITIALIZER
#elif defined (WIN32)
typedef HANDLE MUTEX;

#   define MUTEX_LOCK(arg)      WaitForSingleObject( *(arg), INFINITE )
#   define MUTEX_TRYLOCK(arg)   (WaitForSingleObject( *(arg), 0 ) == WAIT_TIMEOUT ? FALSE : TRUE)
#   define MUTEX_UNLOCK(arg)    ReleaseMutex( *(arg) )
#   define MUTEX_INIT(arg)      (*(arg) = CreateMutex( NULL, FALSE, NULL ))
#   define MUTEX_DESTROY(arg)   CloseHandle( *(arg) )
#   define MUTEX_INITIALIZER    NULL
#else
typedef int MUTEX;

#   define MUTEX_LOCK(arg)      NULL
#   define MUTEX_TRYLOCK(arg)   NULL
#   define MUTEX_UNLOCK(arg)    NULL
#   define MUTEX_INIT(arg)      NULL
#   define MUTEX_DESTROY(arg)   NULL
#   define MUTEX_INITIALIZER    NULL
#endif

/* Macros for multi-threaded portability ------------------------------*/
#if defined (LINUX) || defined (SOLARIS)
typedef pthread_t THREAD;
typedef void *THREAD_FUNC;

#   define THREAD_CREATE(tp,fp,ap) \
        (pthread_create((tp),NULL,(fp),(ap)) ? FALSE : TRUE)
#   define THREAD_JOIN(tid)     pthread_join(tid, NULL)
#   define THREAD_SELF()        (THREAD)pthread_self()
#   define THREAD_EXIT(sp)      pthread_exit((sp))
#   define THREAD_ERRNO         (errno)
#elif defined (WIN32)
typedef HANDLE THREAD;
typedef void THREAD_FUNC;

#   define THREAD_CREATE(tp,fp,ap) \
        (((*(UINT32 *)(tp)) = _beginthread((fp),0,(void*)(ap))) == -1 ? FALSE : TRUE)
#   define THREAD_JOIN(tid)     WaitForSingleObject(tid, INFINITE)
#   define THREAD_SELF()        GetCurrentThreadId()
#   define THREAD_EXIT(sp)      _endthread()
#   define THREAD_ERRNO         WSAGetLastError()
#else
typedef int THREAD;
typedef void THREAD_FUNC;

#   define THREAD_CREATE(tp,fp,ap) NULL
#   define THREAD_JOIN(tid)     NULL
#   define THREAD_SELF()        NULL
#   define THREAD_EXIT(sv)      NULL
#   define THREAD_ERRNO         NULL
#endif

/* Macros for semaphore portability -----------------------------------*/
#if defined (LINUX) || defined (SOLARIS)
#   include <semaphore.h>
typedef sem_t SEMAPHORE;

#   define SEM_INIT(id, init, max) sem_init((id), 0, (unsigned int) (init))
#   define SEM_POST(id)         sem_post(id)
#   define SEM_WAIT(id)         sem_wait(id)
#   define SEM_TRYWAIT(id)      sem_trywait(id)
#   define SEM_DESTROY(id)      sem_destroy(id)
#elif defined (WIN32)
typedef HANDLE SEMAPHORE;

#   define SEM_INIT(id, init, max) (*(id) = CreateSemaphore(NULL, (init), (max), NULL))
#   define SEM_POST(id)         ReleaseSemaphore( *(id), 1, NULL )
#   define SEM_WAIT(id)         WaitForSingleObject( *(id), INFINITE )
#   define SEM_TRYWAIT(id)      (WaitForSingleObject( *(id), 0 ) == WAIT_TIMEOUT ? -1 : 0)
#   define SEM_DESTROY(id)      CloseHandle( *(id) );
#else
typedef int SEMAPHORE;

#   define SEM_INIT(arg1, arg2, arg3) NULL
#   define SEM_POST(arg)        NULL
#   define SEM_WAIT(arg)        NULL
#   define SEM_TRYWAIT(arg)     NULL
#   define SEM_DESTROY(arg)     NULL
#endif

/* Assertion macro ----------------------------------------------------*/
#if defined _ASSERT
#   include <assert.h>
#   define ASSERT(expression) assert(expression);
#else
#   define ASSERT(expression) NULL
#endif										/* defined DEBUG */

#endif										/* PLATFORM_H_INCLUDED */
