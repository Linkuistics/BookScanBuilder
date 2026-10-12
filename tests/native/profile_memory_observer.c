/* Separate test image. Reuse the old observer unchanged, wrapping serialization
   locally to read the same handles, not a profile reconstructed from its bytes. */
#include <lcms2.h>
static cmsBool memory_save_profile(cmsHPROFILE, void *, cmsUInt32Number *);
#define cmsSaveProfileToMem memory_save_profile
#include "target_observer.c"
#undef cmsSaveProfileToMem

static void memory_profile(unsigned seq, cmsHPROFILE profile) {
    char suffix[96];
    if (snprintf(suffix, sizeof(suffix), "%" PRIuPTR "-memory.txt", (uintptr_t)profile) < 0)
        _exit(98);
    FILE *file = reserve(seq, suffix);
    fprintf(file, "memory-v1 %d %u %" PRIuPTR " %u\n", getpid(), seq,
            (uintptr_t)profile, cmsGetEncodedCMMversion());
    /* Public typed tag/segment/estimated-table APIs, exact selected declarations:
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19/include/lcms2.h
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19/src/cmsgamma.c */
    const cmsTagSignature xyz_tags[4] = {
        cmsSigRedColorantTag, cmsSigGreenColorantTag, cmsSigBlueColorantTag, cmsSigMediaWhitePointTag
    };
    const cmsTagSignature curve_tags[3] = {cmsSigRedTRCTag, cmsSigGreenTRCTag, cmsSigBlueTRCTag};
    const cmsCIEXYZ *xyz[4];
    cmsToneCurve *curves[3];
    const cmsCurveSegment *segments[3];
    for (unsigned i = 0; i < 4; i++) {
        xyz[i] = cmsReadTag(profile, xyz_tags[i]);
        if (xyz[i] == NULL) goto unavailable;
    }
    for (unsigned i = 0; i < 3; i++) {
        curves[i] = cmsReadTag(profile, curve_tags[i]);
        if (curves[i] == NULL) goto unavailable;
        segments[i] = cmsGetToneCurveSegment(0, curves[i]);
        if (segments[i] == NULL || cmsGetToneCurveSegment(1, curves[i]) != NULL
            || segments[i]->Type < 1 || segments[i]->Type > 5
            || segments[i]->Type != cmsGetToneCurveParametricType(curves[i])
            || cmsGetToneCurveEstimatedTableEntries(curves[i]) < 2
            || cmsGetToneCurveEstimatedTable(curves[i]) == NULL) goto unavailable;
    }
    fprintf(file, "xyz");
    for (unsigned i = 0; i < 4; i++)
        fprintf(file, " %a %a %a", xyz[i]->X, xyz[i]->Y, xyz[i]->Z);
    fprintf(file, "\n");
    for (unsigned i = 0; i < 3; i++) {
        const cmsCurveSegment *segment = segments[i];
        fprintf(file, "curve %u %d %a %a", i, segment->Type, (double)segment->x0,
                (double)segment->x1);
        for (unsigned j = 0; j < 10; j++) fprintf(file, " %a", segment->Params[j]);
        fprintf(file, "\n");
        cmsUInt32Number count = cmsGetToneCurveEstimatedTableEntries(curves[i]);
        const cmsUInt16Number *table = cmsGetToneCurveEstimatedTable(curves[i]);
        fprintf(file, "table %u %u", i, count);
        for (unsigned j = 0; j < count; j++) fprintf(file, " %u", table[j]);
        fprintf(file, "\n");
    }
    if (ferror(file) || fclose(file) != 0) _exit(99);
    return;
unavailable:
    fprintf(file, "unavailable unsupported-profile\n");
    if (ferror(file) || fclose(file) != 0) _exit(99);
}

static cmsBool memory_save_profile(cmsHPROFILE profile, void *data, cmsUInt32Number *size) {
    /* The pass-through call does not alter profiles or transform settings. */
    if (data != NULL) memory_profile(atomic_load(&sequence), profile);
    return cmsSaveProfileToMem(profile, data, size);
}
