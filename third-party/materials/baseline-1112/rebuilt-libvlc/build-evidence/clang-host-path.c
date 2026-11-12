#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* Host-only: WSL1 cannot load BOLT's extra executable segment directly.
 * When ld.so starts Clang, keep Clang's spawned frontend at our shell entry. */
ssize_t readlink(const char *path, char *buffer, size_t size) {
    const char *entry = getenv("AURORA_CLANG_HOST_ENTRY");
    if (entry && program_invocation_short_name && strncmp(program_invocation_short_name, "clang", 5) == 0 && strcmp(path, "/proc/self/exe") == 0) {
        size_t length = strlen(entry);
        if (length > size) length = size;
        memcpy(buffer, entry, length);
        return (ssize_t)length;
    }
    ssize_t (*original)(const char *, char *, size_t) = dlsym(RTLD_NEXT, "readlink");
    if (!original) { errno = ENOSYS; return -1; }
    return original(path, buffer, size);
}
