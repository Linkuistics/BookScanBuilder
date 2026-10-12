/* Test child only. Exact 2.19.1 header/binary-bound ABI, never a product API. */
#include "lcms2_internal.h"
#include <dlfcn.h>
#include <stddef.h>
#define __attribute__(x)
#include "profile_memory_observer.c"
#undef __attribute__

static void final_pipeline(unsigned seq, cmsHTRANSFORM transform,
                           cmsHPROFILE input, cmsHPROFILE target, double adaptation) {
    /* The checked native binary frees Lut at offset 0x70 and GamutCheck at 0x78.
       Compile exact official header; compare all available public getters BEFORE
       using the final Lut. Capture real worker-module identity and probe binding.
       This is a bounded test ABI, not a portable or supported product accessor.
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/lcms2_internal.h
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmsopt.c
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmsxform.c */
    const _cmsTRANSFORM *cargo = transform;
    cmsFormatter16 from = NULL, to = NULL;
    _cmsGetTransformFormatters16(transform, &from, &to);
    size_t offset = offsetof(_cmsTRANSFORM, Lut);
#ifdef BOOKSCAN_TEST_WRONG_ABI
    offset += 8; /* Private actual-child control; rejected before any Lut read. */
#endif
    if (cmsGetEncodedCMMversion() != 2190 || offset != 112
        || offsetof(_cmsTRANSFORM, GamutCheck) != 120
        || cargo->InputFormat != cmsGetTransformInputFormat(transform)
        || cargo->OutputFormat != cmsGetTransformOutputFormat(transform)
        || cargo->dwOriginalFlags != _cmsGetTransformFlags(transform)
        || cargo->FromInput != from || cargo->ToOutput != to
        || cargo->ContextID != cmsGetTransformContextID(transform)
        || cargo->Worker != _cmsGetTransformWorker(transform)
        || cargo->UserData != _cmsGetTransformUserData(transform)
        || cargo->RenderingIntent != 1 || cargo->GamutCheck != NULL || cargo->xform == NULL)
        _exit(110);
    cmsPipeline *lut = cargo->Lut;
    if (lut == NULL || cmsPipelineInputChannels(lut) != 3
        || cmsPipelineOutputChannels(lut) != 3) _exit(111);
    FILE *file = reserve(seq, "pipeline.txt");
    fprintf(file, "pipeline-v1 %d %u %" PRIuPTR " %u %u %u %u %" PRIuPTR " %u\n",
        getpid(), seq, (uintptr_t)transform, cmsGetTransformInputFormat(transform),
        cmsGetTransformOutputFormat(transform), _cmsGetTransformFlags(transform),
        cmsGetEncodedCMMversion(), (uintptr_t)lut, cmsPipelineStageCount(lut));
    fprintf(file, "creation %" PRIuPTR " %" PRIuPTR " 1 1 1 1 %a %a\n",
        (uintptr_t)input, (uintptr_t)target, adaptation,
        cmsSetAdaptationStateTHR(cargo->ContextID, -1));
    unsigned index = 0;
    for (cmsStage *stage = cmsPipelineGetPtrToFirstStage(lut); stage;
         stage = cmsStageNext(stage), index++) {
        if (cmsStageInputChannels(stage) != 3 || cmsStageOutputChannels(stage) != 3)
            _exit(112);
        fprintf(file, "stage %u %u 3 3\n", index, cmsStageType(stage));
        /* Public plugin stage-data structures, not transform/pipeline internals.
           https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/include/lcms2_plugin.h */
        if (cmsStageType(stage) == cmsSigMatrixElemType) {
            const _cmsStageMatrixData *data = cmsStageData(stage);
            if (!data || !data->Double) _exit(113);
            fprintf(file, "matrix %d", data->Offset != NULL);
            for (unsigned i = 0; i < 9; i++) fprintf(file, " %a", data->Double[i]);
            for (unsigned i = 0; i < 3; i++)
                fprintf(file, " %a", data->Offset ? data->Offset[i] : 0.0);
            fprintf(file, "\n");
        } else if (cmsStageType(stage) == cmsSigCurveSetElemType) {
            const _cmsStageToneCurvesData *data = cmsStageData(stage);
            if (!data || data->nCurves != 3 || !data->TheCurves) _exit(114);
            for (unsigned c = 0; c < 3; c++) {
                const cmsToneCurve *curve = data->TheCurves[c];
                const cmsCurveSegment *s = cmsGetToneCurveSegment(0, curve);
                if (!s || cmsGetToneCurveSegment(1, curve)
                    || s->Type != cmsGetToneCurveParametricType(curve)) _exit(115);
                fprintf(file, "curve %u %d %a %a", c, s->Type, (double)s->x0, (double)s->x1);
                for (unsigned i = 0; i < 10; i++) fprintf(file, " %a", s->Params[i]);
                fprintf(file, "\n");
            }
        } else _exit(116);
    }
    if (index != cmsPipelineStageCount(lut)) _exit(117);
    for (unsigned v = 0; v < 256; v++) {
        cmsUInt8Number source[3] = {v, 255-v, (v*73)%256}, actual[3];
        cmsUInt16Number words[3], result[3];
        for (unsigned c = 0; c < 3; c++) words[c] = source[c]*257;
        cmsPipelineEval16(words, result, lut);
        cmsDoTransform(transform, source, actual, 1);
        fprintf(file, "probe %u %u %u %u %u %u %u\n", v, result[0], result[1], result[2],
            actual[0], actual[1], actual[2]);
    }
    if (ferror(file) || fclose(file)) _exit(118);
    Dl_info info;
    if (!dladdr((const void *)cargo->xform, &info) || !info.dli_fname || !info.dli_fbase)
        _exit(119);
    file = reserve(seq, "evaluator-pipeline-module.txt");
    fprintf(file, "module-v1 %d %u evaluator %" PRIuPTR " %" PRIuPTR "\n%s\n",
        getpid(), seq, (uintptr_t)cargo->xform, (uintptr_t)info.dli_fbase, info.dli_fname);
    if (ferror(file) || fclose(file)) _exit(120);
}

static cmsHTRANSFORM pipeline_transform(cmsHPROFILE input, cmsUInt32Number in,
        cmsHPROFILE target, cmsUInt32Number out, cmsUInt32Number intent, cmsUInt32Number flags) {
    (void)hooks;
    int selected = (in == 262169 || in == 25) && out == 262169;
    double adaptation = cmsSetAdaptationStateTHR(cmsGetProfileContextID(input), -1);
    if (selected && (flags != 8448 || intent != 1)) _exit(121);
    cmsHTRANSFORM result = observed_transform(input, in, target, out, intent, flags);
    if (selected) {
        if (!result) _exit(122);
        final_pipeline(atomic_load(&sequence), result, input, target, adaptation);
    }
    return result;
}

__attribute__((used, section("__DATA,__interpose")))
static const struct { const void *replacement; const void *original; } pipeline_hooks[] = {
    { (const void *)observed_srgb, (const void *)cmsCreate_sRGBProfile },
    { (const void *)pipeline_transform, (const void *)cmsCreateTransform }
};
