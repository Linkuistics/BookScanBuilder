/* Actual child only; prior header/binary-checked pipeline observer stays exact. */
#define __attribute__(x)
#include "transform_pipeline_observer.c"
#undef __attribute__

#include <float.h>
#include <string.h>

static void source_gamma(unsigned seq, cmsHTRANSFORM transform, cmsHPROFILE input) {
    /* pipeline_transform has already verified this exact transform ABI and Lut.
       Read only public stage data and call the public curve evaluator; no curve
       or stage private layout. Actual stage dispatch remains a separate claim.
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmsgamma.c
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmslut.c */
    _Static_assert(sizeof(float) == 4 && FLT_RADIX == 2 && FLT_MANT_DIG == 24,
                   "Requires IEEE binary32");
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error Test transcript requires little endian
#endif
    const _cmsTRANSFORM *cargo = transform;
    cmsStage *stage = cmsPipelineGetPtrToFirstStage(cargo->Lut);
    if (!stage || cmsStageType(stage) != cmsSigCurveSetElemType) _exit(130);
    const _cmsStageToneCurvesData *data = cmsStageData(stage);
    if (!data || data->nCurves != 3 || !data->TheCurves) _exit(131);
    FILE *file = reserve(seq, "gamma.txt");
    fprintf(file, "gamma-v1 %d %u %" PRIuPTR " %" PRIuPTR " %u %u %u %u 65536\n",
        getpid(), seq, (uintptr_t)transform, (uintptr_t)input,
        cmsGetTransformInputFormat(transform), cmsGetTransformOutputFormat(transform),
        _cmsGetTransformFlags(transform), cmsGetEncodedCMMversion());
    for (unsigned c = 0; c < 3; c++) {
        const cmsToneCurve *curve = data->TheCurves[c];
        const cmsCurveSegment *s = cmsGetToneCurveSegment(0, curve);
        if (!s || cmsGetToneCurveSegment(1, curve) || s->Type != 1 || s->Params[0] != 2.0)
            _exit(132);
        fprintf(file, "channel %u %" PRIuPTR " %d %a\n", c, (uintptr_t)curve,
                s->Type, s->Params[0]);
        char name[32];
        if (snprintf(name, sizeof(name), "gamma-%u.bin", c) < 0) _exit(133);
        FILE *codes = reserve(seq, name);
        for (unsigned v = 0; v < 65536; v++) {
            float x = (float)((double)v / 65535.0);
            float y = cmsEvalToneCurveFloat(curve, x);
            uint32_t pair[2];
            memcpy(&pair[0], &x, 4); memcpy(&pair[1], &y, 4);
            if (fwrite(pair, sizeof(pair), 1, codes) != 1) _exit(134);
        }
        if (ferror(codes) || fclose(codes)) _exit(135);
    }
    if (ferror(file) || fclose(file)) _exit(136);
    Dl_info info;
    if (!dladdr((const void *)cmsEvalToneCurveFloat, &info) || !info.dli_fname || !info.dli_fbase)
        _exit(137);
    file = reserve(seq, "gamma-module.txt");
    fprintf(file, "gamma-module-v1 %d %u %" PRIuPTR " %" PRIuPTR "\n%s\n",
        getpid(), seq, (uintptr_t)cmsEvalToneCurveFloat, (uintptr_t)info.dli_fbase, info.dli_fname);
    if (ferror(file) || fclose(file)) _exit(138);
}

static cmsHTRANSFORM gamma_transform(cmsHPROFILE input, cmsUInt32Number in,
        cmsHPROFILE target, cmsUInt32Number out, cmsUInt32Number intent, cmsUInt32Number flags) {
    (void)pipeline_hooks;
    cmsHTRANSFORM result = pipeline_transform(input, in, target, out, intent, flags);
    if ((in == 262169 || in == 25) && out == 262169)
        source_gamma(atomic_load(&sequence), result, input);
    return result;
}

__attribute__((used, section("__DATA,__interpose")))
static const struct { const void *replacement; const void *original; } gamma_hooks[] = {
    { (const void *)observed_srgb, (const void *)cmsCreate_sRGBProfile },
    { (const void *)gamma_transform, (const void *)cmsCreateTransform }
};
