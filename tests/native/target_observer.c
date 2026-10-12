/* Test-owned pass-through observation; never packaged or used by product import. */
#include <fcntl.h>
#include <inttypes.h>
#include <lcms2.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static _Atomic unsigned sequence;

static FILE *reserve(unsigned seq, const char *suffix) {
    const char *dir = getenv("BOOKSCAN_TEST_PROFILE_DIR");
    char path[4096];
    int n = dir == NULL ? -1 : snprintf(path, sizeof(path), "%s/%d-%u-%s", dir, getpid(), seq, suffix);
    if (n < 0 || (size_t)n >= sizeof(path)) _exit(91);
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    if (fd < 0) _exit(92);
    FILE *file = fdopen(fd, "wb");
    if (file == NULL) _exit(93);
    return file;
}

static void save(unsigned seq, const char *suffix, cmsHPROFILE profile) {
    /* Exact 2.19 API: serialize the actual supplied handle; never create a replacement.
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19/include/lcms2.h */
    cmsUInt32Number size = 0;
    if (profile == NULL || !cmsSaveProfileToMem(profile, NULL, &size) || size == 0) _exit(94);
    void *data = malloc(size);
    if (data == NULL || !cmsSaveProfileToMem(profile, data, &size)) _exit(95);
    FILE *file = reserve(seq, suffix);
    if (fwrite(data, 1, size, file) != size || fclose(file) != 0) _exit(96);
    free(data);
}

static void record(unsigned seq, const char *kind, cmsHPROFILE input, cmsHPROFILE target,
                   cmsHTRANSFORM transform, cmsUInt32Number in, cmsUInt32Number out,
                   cmsUInt32Number intent, cmsUInt32Number flags) {
    FILE *file = reserve(seq, "event.txt");
    if (fprintf(file, "v1 %d %u %s %" PRIuPTR " %" PRIuPTR " %" PRIuPTR
                " %u %u %u %u %u\n", getpid(), seq, kind, (uintptr_t)input, (uintptr_t)target,
                (uintptr_t)transform, in, out, intent, flags, cmsGetEncodedCMMversion()) < 0
        || fclose(file) != 0) _exit(97);
}

static cmsHPROFILE observed_srgb(void) {
    cmsHPROFILE result = cmsCreate_sRGBProfile();
    unsigned seq = atomic_fetch_add(&sequence, 1) + 1;
    save(seq, "target.icc", result);
    record(seq, "srgb", NULL, result, NULL, 0, 0, 0, 0);
    return result;
}

static cmsHTRANSFORM observed_transform(cmsHPROFILE input, cmsUInt32Number in,
                                      cmsHPROFILE target, cmsUInt32Number out,
                                      cmsUInt32Number intent, cmsUInt32Number flags) {
    cmsHTRANSFORM result = cmsCreateTransform(input, in, target, out, intent, flags);
    unsigned seq = atomic_fetch_add(&sequence, 1) + 1;
    save(seq, "input.icc", input);
    save(seq, "target.icc", target);
    record(seq, "transform", input, target, result, in, out, intent, flags);
    return result;
}

/* References within this image call the original functions. Actual child controls
   verify interception and pass-through pixels on this Mac, rather than assuming it.
   https://raw.githubusercontent.com/apple-oss-distributions/dyld/main/include/mach-o/dyld-interposing.h */
/* This arm64 host's SDK does not ship the public interposing header. Emit its
   documented two-pointer section directly; no arm64e/ptrauth portability claim. */
__attribute__((used, section("__DATA,__interpose")))
static const struct { const void *replacement; const void *original; } hooks[] = {
    { (const void *)observed_srgb, (const void *)cmsCreate_sRGBProfile },
    { (const void *)observed_transform, (const void *)cmsCreateTransform }
};
