/* Separate test image: preserve prior observations without changing their source. */
#include <lcms2_plugin.h>
#include <dlfcn.h>
#include <string.h>
/* The prior hook array is retained as ordinary data, not a competing interpose
   registration. The two pass-through functions below own this image's hooks. */
#define __attribute__(x)
#include "profile_memory_observer.c"
#undef __attribute__

static void formatter_module(unsigned seq, const char *role, const void *function) {
    Dl_info info;
    if (!dladdr(function, &info) || info.dli_fname == NULL || info.dli_fbase == NULL) _exit(101);
    char suffix[96];
    snprintf(suffix, sizeof(suffix), "%s-formatter-module.txt", role);
    FILE *file = reserve(seq, suffix);
    fprintf(file, "module-v1 %d %u %s %" PRIuPTR " %" PRIuPTR "\n%s\n",
            getpid(), seq, role, (uintptr_t)function, (uintptr_t)info.dli_fbase, info.dli_fname);
    if (ferror(file) || fclose(file)) _exit(102);
}

static cmsHTRANSFORM formatter_transform(cmsHPROFILE input, cmsUInt32Number in,
                                        cmsHPROFILE target, cmsUInt32Number out,
                                        cmsUInt32Number intent, cmsUInt32Number flags) {
    (void)hooks;
    cmsHTRANSFORM result = observed_transform(input, in, target, out, intent, flags);
    unsigned seq = atomic_load(&sequence);
    if ((in != 262169 && in != 25) || out != 262169) return result;
    if (result == NULL) _exit(103);
    struct _cmstransform_struct *cargo = result;
    cmsFormatter16 from = NULL, to = NULL;
    /* Public plugin accessors read current formatters without registering a plugin.
       Flags are ORIGINAL flags; never infer final optimization state from them.
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19/include/lcms2_plugin.h
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19/src/cmsxform.c */
    _cmsGetTransformFormatters16(cargo, &from, &to);
    if (from == NULL || to == NULL) _exit(104);
    FILE *file = reserve(seq, "formatter.bin");
    fprintf(file, "formatter-v1 %d %u %" PRIuPTR " %u %u %u %u\nfunctions %" PRIuPTR
            " %" PRIuPTR "\n", getpid(), seq, (uintptr_t)result,
            cmsGetTransformInputFormat(result), cmsGetTransformOutputFormat(result),
            _cmsGetTransformFlags(cargo), cmsGetEncodedCMMversion(), (uintptr_t)from, (uintptr_t)to);
    /* Exhaust each channel with distinct bijective permutations. Guards and
       exact returned-buffer advance detect unexpected layouts before retention.
       The Python oracle independently declares expansion/rounding before render.
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19/src/cmspack.c */
    for (unsigned v = 0; v < 256; v++) {
        cmsUInt8Number buffer[5] = { 0xA5, v, 255-v, (v*73)%256, 0x5A };
        cmsUInt16Number words[cmsMAXCHANNELS];
        for (unsigned i = 0; i < cmsMAXCHANNELS; i++) words[i] = 0xA55A;
        cmsUInt8Number *end = from(cargo, words, buffer+1, 0);
        if (end != buffer+4 || buffer[0] != 0xA5 || buffer[4] != 0x5A
            || buffer[1] != v || buffer[2] != 255-v || buffer[3] != (v*73)%256) _exit(105);
        for (unsigned i = 3; i < cmsMAXCHANNELS; i++) if (words[i] != 0xA55A) _exit(105);
        for (unsigned c = 0; c < 3; c++) { fputc(words[c] >> 8, file); fputc(words[c] & 255, file); }
    }
    for (unsigned v = 0; v < 65536; v++) {
        cmsUInt16Number words[cmsMAXCHANNELS] = {v, 65535-v, (v*73)%65536};
        cmsUInt16Number before[cmsMAXCHANNELS];
        memcpy(before, words, sizeof(words));
        cmsUInt8Number buffer[5] = {0xA5, 0, 0, 0, 0x5A};
        cmsUInt8Number *end = to(cargo, words, buffer+1, 0);
        if (end != buffer+4 || buffer[0] != 0xA5 || buffer[4] != 0x5A
            || memcmp(before, words, sizeof(words))) _exit(106);
        if (fwrite(buffer+1, 1, 3, file) != 3) _exit(107);
    }
    if (ferror(file) || fclose(file)) _exit(108);
    formatter_module(seq, "input", (const void *)from);
    formatter_module(seq, "output", (const void *)to);
    return result;
}

/* Exact tested arm64 interpose mechanism, preserving the original SRGB hook.
   https://raw.githubusercontent.com/apple-oss-distributions/dyld/main/include/mach-o/dyld-interposing.h */
__attribute__((used, section("__DATA,__interpose")))
static const struct { const void *replacement; const void *original; } formatter_hooks[] = {
    { (const void *)observed_srgb, (const void *)cmsCreate_sRGBProfile },
    { (const void *)formatter_transform, (const void *)cmsCreateTransform }
};
