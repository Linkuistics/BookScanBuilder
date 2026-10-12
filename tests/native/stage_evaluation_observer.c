/* Test child only; keep every earlier observer byte-exact through inclusion. */
#define __attribute__(x)
#include "source_gamma_observer.c"
#undef __attribute__

static void stage_evaluation(unsigned seq, cmsHTRANSFORM transform) {
    /* Exact official header plus native constructor/getter/Evaluate* disassembly.
       This private stage layout is only a bound test ABI, never a product API.
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/lcms2_internal.h
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmslut.c */
    size_t offset = offsetof(cmsStage, EvalPtr);
#ifdef BOOKSCAN_TEST_WRONG_STAGE_ABI
    offset += 8;
#endif
    if (cmsGetEncodedCMMversion() != 2190 || offset != 24
        || offsetof(cmsStage, Data) != 48 || offsetof(cmsStage, Next) != 56
        || offsetof(cmsStage, InputChannels) != 16 || offsetof(cmsStage, OutputChannels) != 20
        || offsetof(cmsStage, Type) != 8) _exit(150);
    uint64_t fpcr;
    __asm__ volatile("mrs %0, fpcr" : "=r"(fpcr));
    if (fpcr != 0) _exit(151); /* Nearest-even, no flush-to-zero. */
    const _cmsTRANSFORM *cargo = transform;
    cmsStage *stages[2] = {cmsPipelineGetPtrToFirstStage(cargo->Lut), NULL};
    if (!stages[0]) _exit(152);
    stages[1] = cmsStageNext(stages[0]);
    if (!stages[1]) _exit(153);
    FILE *file = reserve(seq, "stage-dispatch.txt");
    fprintf(file, "stage-dispatch-v1 %d %u %" PRIuPTR " %" PRIuPTR " 65536\n",
            getpid(), seq, (uintptr_t)transform, (uintptr_t)cargo->Lut);
    for (unsigned s = 0; s < 2; s++) {
        const cmsStage *stage = stages[s];
        if (stage->Type != cmsStageType(stage) || stage->Data != cmsStageData(stage)
            || stage->Next != cmsStageNext(stage)
            || stage->InputChannels != cmsStageInputChannels(stage)
            || stage->OutputChannels != cmsStageOutputChannels(stage)
            || stage->InputChannels != 3 || stage->OutputChannels != 3 || !stage->EvalPtr
            || stage->Type != (s ? cmsSigMatrixElemType : cmsSigCurveSetElemType)) _exit(154);
        Dl_info info;
        if (!dladdr((const void *)stage->EvalPtr, &info) || !info.dli_fname || !info.dli_fbase)
            _exit(155);
        fprintf(file, "stage %u %" PRIuPTR " %u 3 3 %" PRIuPTR " %" PRIuPTR " %" PRIuPTR "\n%s\n",
                s, (uintptr_t)stage, stage->Type, (uintptr_t)stage->EvalPtr,
                (uintptr_t)info.dli_fbase, (uintptr_t)stage->Data, info.dli_fname);
    }
    fprintf(file, "abi %zu 48 56 16 20 8 fpcr %" PRIu64 "\n", offset, fpcr);
    if (ferror(file) || fclose(file)) _exit(156);
    const _cmsStageMatrixData *matrix = cmsStageData(stages[1]);
    if (!matrix || !matrix->Double || matrix->Offset) _exit(157);
    FILE *codes = reserve(seq, "stage-vectors.bin");
    for (unsigned v = 0; v < 65536; v++) {
        unsigned words[3] = {v, 65535-v, (v*73)%65536};
        float x[3], source[3], out[3];
        for (unsigned c = 0; c < 3; c++) x[c] = (float)((double)words[c] / 65535.0);
        stages[0]->EvalPtr(x, source, stages[0]);
        stages[1]->EvalPtr(source, out, stages[1]);
        uint32_t bits[9];
        memcpy(bits, x, 12); memcpy(bits+3, source, 12); memcpy(bits+6, out, 12);
        if (fwrite(bits, sizeof(bits), 1, codes) != 1) _exit(158);
    }
    if (ferror(codes) || fclose(codes)) _exit(159);
}

static cmsHTRANSFORM stage_transform(cmsHPROFILE input, cmsUInt32Number in,
        cmsHPROFILE target, cmsUInt32Number out, cmsUInt32Number intent, cmsUInt32Number flags) {
    (void)gamma_hooks;
    cmsHTRANSFORM result = gamma_transform(input, in, target, out, intent, flags);
    if ((in == 262169 || in == 25) && out == 262169)
        stage_evaluation(atomic_load(&sequence), result);
    return result;
}

__attribute__((used, section("__DATA,__interpose")))
static const struct { const void *replacement; const void *original; } stage_hooks[] = {
    { (const void *)observed_srgb, (const void *)cmsCreate_sRGBProfile },
    { (const void *)stage_transform, (const void *)cmsCreateTransform }
};
