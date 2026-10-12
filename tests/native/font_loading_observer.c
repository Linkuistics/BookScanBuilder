/* Test-only pass-through observation on this Mac arm64 host. No product injection. */
#include <errno.h>
#include <fcntl.h>
#include <fontconfig/fontconfig.h>
#include <ft2build.h>
#include FT_FREETYPE_H
#include <inttypes.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#if FC_VERSION != 21803 || FREETYPE_MAJOR != 2 || FREETYPE_MINOR != 14 || FREETYPE_PATCH != 3
#error "Observer requires Fontconfig 2.18.3 and FreeType 2.14.3 headers"
#endif

static _Atomic unsigned sequence, calls;
static _Thread_local unsigned face_call;

static int scoped(const char *path) {
    const char *root = getenv("BOOKSCAN_TEST_FONT_ROOT");
    return root != NULL && path != NULL && strncmp(path, root, strlen(root)) == 0
        && path[strlen(root)] == '/';
}

static void quoted(FILE *file, const char *value) {
    if (fputc('"', file) == EOF) _exit(94);
    for (const unsigned char *p = (const unsigned char *)value; *p; p++) {
        if (*p < 32 || *p == '"' || *p == '\\') {
            if (fprintf(file, "\\u%04x", *p) < 0) _exit(94);
        } else if (fputc(*p, file) == EOF) _exit(94);
    }
    if (fputc('"', file) == EOF) _exit(94);
}

static FILE *event(const char *kind, const char *path) {
    const char *dir = getenv("BOOKSCAN_TEST_FONT_EVENTS");
    unsigned seq = atomic_fetch_add(&sequence, 1) + 1;
    char name[4096];
    int n = dir == NULL ? -1 : snprintf(name, sizeof(name), "%s/%d-%08u.json", dir, getpid(), seq);
    if (n < 0 || (size_t)n >= sizeof(name)) _exit(91);
    int fd = open(name, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    FILE *file = fd < 0 ? NULL : fdopen(fd, "wb");
    if (file == NULL) _exit(92);
    if (fprintf(file, "{\"version\":1,\"pid\":%d,\"sequence\":%u,\"kind\":", getpid(), seq) < 0)
        _exit(93);
    quoted(file, kind);
    if (fputs(",\"path\":", file) == EOF) _exit(93);
    quoted(file, path);
    return file;
}

static void end(FILE *file) {
    if (fputs("}\n", file) == EOF || fclose(file) != 0) _exit(95);
}

static void selected(FcPattern *pattern, const char *api) {
    FcChar8 *path = NULL;
    int index = -1;
    /* The public 2.18.3 pattern accessors return a result code; do not guess defaults.
       https://github.com/fontconfig/fontconfig/blob/2.18.3/fontconfig/fontconfig.h */
    if (pattern == NULL || FcPatternGetString(pattern, FC_FILE, 0, &path) != FcResultMatch
        || FcPatternGetInteger(pattern, FC_INDEX, 0, &index) != FcResultMatch
        || !scoped((const char *)path)) return;
    FILE *file = event("match", (const char *)path);
    if (fprintf(file, ",\"index\":%d", index) < 0) _exit(93);
    if (fputs(",\"api\":", file) == EOF) _exit(93);
    quoted(file, api);
    end(file);
}

static FcPattern *observed_match(FcConfig *config, FcPattern *pattern, FcResult *result) {
    FcPattern *found = FcFontMatch(config, pattern, result);
    int saved = errno;
    selected(found, "FcFontMatch");
    errno = saved;
    return found;
}

static FcFontSet *observed_sort(FcConfig *config, FcPattern *pattern, FcBool trim,
                              FcCharSet **coverage, FcResult *result) {
    FcFontSet *found = FcFontSort(config, pattern, trim, coverage, result);
    int saved = errno;
    if (found != NULL) for (int i = 0; i < found->nfont; i++) selected(found->fonts[i], "FcFontSort");
    errno = saved;
    return found;
}

static int observed_open(const char *path, int flags, ...) {
    int fd;
    if (flags & O_CREAT) {
        va_list args;
        va_start(args, flags);
        int mode = va_arg(args, int);
        va_end(args);
        fd = open(path, flags, mode);
    } else fd = open(path, flags);
    int saved = errno;
    if (fd >= 0 && face_call != 0 && scoped(path)) {
        struct stat value;
        if (fstat(fd, &value) != 0) _exit(96);
        FILE *file = event("open", path);
        if (fprintf(file, ",\"call\":%u,\"device\":%" PRIuMAX ",\"inode\":%" PRIuMAX
                    ",\"size\":%" PRIdMAX, face_call, (uintmax_t)value.st_dev,
                    (uintmax_t)value.st_ino, (intmax_t)value.st_size) < 0) _exit(93);
        end(file);
    }
    errno = saved;
    return fd;
}

static FT_Error observed_face(FT_Library library, const char *path, FT_Long index,
                              FT_Face *face) {
    unsigned previous = face_call;
    face_call = atomic_fetch_add(&calls, 1) + 1;
    /* Exact public FreeType 2.14.3 API: pass original args; retain its real result.
       https://freetype.org/freetype2/docs/reference/ft2-face_creation.html#ft_new_face */
    FT_Error result = FT_New_Face(library, path, index, face);
    int saved = errno;
    if (scoped(path)) {
        FILE *file = event("face", path);
        if (fprintf(file, ",\"call\":%u,\"index\":%ld,\"error\":%d", face_call,
                    result == 0 && face != NULL && *face != NULL ? (*face)->face_index : index,
                    result) < 0) _exit(93);
        end(file);
    }
    face_call = previous;
    errno = saved;
    return result;
}

/* References from this image call originals; actual disabled/byte controls test that.
   https://github.com/apple-oss-distributions/dyld/blob/main/include/mach-o/dyld-interposing.h */
__attribute__((used, section("__DATA,__interpose")))
static const struct { const void *replacement; const void *original; } hooks[] = {
    { (const void *)observed_match, (const void *)FcFontMatch },
    { (const void *)observed_sort, (const void *)FcFontSort },
    { (const void *)observed_face, (const void *)FT_New_Face },
    { (const void *)observed_open, (const void *)open }
};
