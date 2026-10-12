/* Separate synchronous test child; preserve every prior observer by inclusion. */
#define __attribute__(x)
#include "stage_evaluation_observer.c"
#undef __attribute__

static cmsPipeline *trace_lut;
static cmsStage *trace_stages[3];
static _cmsStageEvalFn trace_original[3];
static _cmsPipelineEval16Fn trace_eval16;
static uint32_t trace_row[34];
static unsigned trace_phase, trace_calls, trace_stage_calls;

static void trace_stage(const float in[], float out[], const cmsStage *stage) {
    unsigned s = trace_phase;
    if (s >= 3 || stage != trace_stages[s]) _exit(161);
    memcpy(trace_row + 7 + 6*s, in, 12);
    trace_original[s](in, out, stage);
    memcpy(trace_row + 10 + 6*s, out, 12);
    trace_phase++;
    trace_stage_calls++;
}

static void trace_pipeline(const cmsUInt16Number in[], cmsUInt16Number out[], const void *data) {
    if (data != trace_lut || trace_phase != 0) _exit(162);
    for (unsigned c = 0; c < 3; c++) trace_row[4+c] = in[c];
    trace_eval16(in, out, data);
    if (trace_phase != 3) _exit(162);
    for (unsigned c = 0; c < 3; c++) trace_row[25+c] = out[c];
    trace_calls++;
}

static void traversal(unsigned seq, cmsHTRANSFORM transform) {
    /* Official 2.19.1 pipeline/stage ABI, checked against this native binary's
       public getters, constructor and CachedXFORM/LUT instructions.
       Wrappers delegate unchanged; no plugin, copied pipeline or replacement CMM.
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmslut.c
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmsxform.c */
    size_t eval_offset = offsetof(cmsPipeline, Eval16Fn);
#ifdef BOOKSCAN_TEST_WRONG_PIPELINE_ABI
    eval_offset += 8;
#endif
    if (eval_offset != 24 || offsetof(cmsPipeline, Data) != 16
        || offsetof(cmsPipeline, Elements) != 0 || offsetof(cmsPipeline, InputChannels) != 8
        || offsetof(cmsPipeline, OutputChannels) != 12) _exit(160);
    _cmsTRANSFORM *cargo = transform;
    trace_lut = cargo->Lut;
    if (!trace_lut || trace_lut->Data != trace_lut || !trace_lut->Eval16Fn
        || trace_lut->Elements != cmsPipelineGetPtrToFirstStage(trace_lut)
        || trace_lut->InputChannels != cmsPipelineInputChannels(trace_lut)
        || trace_lut->OutputChannels != cmsPipelineOutputChannels(trace_lut)
        || cmsPipelineStageCount(trace_lut) != 3) _exit(160);
    cmsPipeline saved_lut;
    cmsStage saved_stages[3];
    memcpy(&saved_lut, trace_lut, sizeof(saved_lut));
    trace_eval16 = trace_lut->Eval16Fn;
    FILE *header = reserve(seq, "traversal.txt");
    fprintf(header, "traversal-v1 %d %u %" PRIuPTR " %" PRIuPTR " 256\n",
            getpid(), seq, (uintptr_t)transform, (uintptr_t)trace_lut);
    Dl_info info;
    if (!dladdr((const void *)trace_eval16, &info) || !info.dli_fname || !info.dli_fbase)
        _exit(163);
    fprintf(header, "lut16 %" PRIuPTR " %" PRIuPTR " %" PRIuPTR "\n%s\n",
            (uintptr_t)trace_eval16, (uintptr_t)info.dli_fbase,
            (uintptr_t)trace_lut->Data, info.dli_fname);
    cmsStage *stage = trace_lut->Elements;
    for (unsigned s = 0; s < 3; s++) {
        if (!stage || !stage->EvalPtr || stage->InputChannels != 3 || stage->OutputChannels != 3
            || stage->Type != (s == 1 ? cmsSigMatrixElemType : cmsSigCurveSetElemType)
            || stage->Type != cmsStageType(stage) || stage->Data != cmsStageData(stage)
            || stage->Next != cmsStageNext(stage)) _exit(164);
        trace_stages[s] = stage;
        memcpy(saved_stages+s, stage, sizeof(*stage));
        trace_original[s] = stage->EvalPtr;
        if (!dladdr((const void *)stage->EvalPtr, &info) || !info.dli_fname || !info.dli_fbase)
            _exit(163);
        fprintf(header, "stage %u %" PRIuPTR " %u 3 3 %" PRIuPTR " %" PRIuPTR
                " %" PRIuPTR " %" PRIuPTR "\n%s\n", s, (uintptr_t)stage, stage->Type,
                (uintptr_t)stage->EvalPtr, (uintptr_t)info.dli_fbase,
                (uintptr_t)stage->Data, (uintptr_t)stage->Next, info.dli_fname);
        stage = stage->Next;
    }
    if (stage) _exit(164);
    FILE *vectors = reserve(seq, "traversal.bin");
    trace_calls = trace_stage_calls = 0;
    for (unsigned v = 0; v < 256; v++) {
        unsigned char in[3] = {v, 255-v, (v*73)%256}, observed[3], restored[3];
        memset(trace_row, 0, sizeof(trace_row));
        trace_row[0] = v;
        for (unsigned c = 0; c < 3; c++) trace_row[1+c] = in[c];
        for (unsigned s = 0; s < 3; s++) trace_stages[s]->EvalPtr = trace_stage;
#ifdef BOOKSCAN_TEST_BYPASS_STAGE
        trace_stages[2]->EvalPtr = trace_original[2];
#endif
        trace_lut->Eval16Fn = trace_pipeline;
        trace_phase = 0;
        cmsDoTransform(transform, in, observed, 1);
        if (trace_phase != 3 || trace_calls != v+1 || trace_stage_calls != 3*(v+1)) _exit(165);
        for (unsigned s = 0; s < 3; s++) {
            trace_stages[s]->EvalPtr = trace_original[s];
            if (memcmp(trace_stages[s], saved_stages+s, sizeof(cmsStage))) _exit(166);
        }
        trace_lut->Eval16Fn = trace_eval16;
        if (memcmp(trace_lut, &saved_lut, sizeof(cmsPipeline))) _exit(166);
        cmsDoTransform(transform, in, restored, 1);
        if (memcmp(observed, restored, 3)) _exit(167);
        for (unsigned c = 0; c < 3; c++) {
            trace_row[28+c] = observed[c]; trace_row[31+c] = restored[c];
        }
        if (fwrite(trace_row, sizeof(trace_row), 1, vectors) != 1) _exit(168);
    }
    fprintf(header, "calls %u %u restored 1 abi 16 24\n", trace_calls, trace_stage_calls);
    if (ferror(vectors) || fclose(vectors) || ferror(header) || fclose(header)) _exit(169);
    trace_lut = NULL;
}

static cmsHTRANSFORM traversal_transform(cmsHPROFILE input, cmsUInt32Number in,
        cmsHPROFILE target, cmsUInt32Number out, cmsUInt32Number intent, cmsUInt32Number flags) {
    (void)stage_hooks;
    cmsHTRANSFORM result = stage_transform(input, in, target, out, intent, flags);
    if ((in == 262169 || in == 25) && out == 262169)
        traversal(atomic_load(&sequence), result);
    return result;
}

__attribute__((used, section("__DATA,__interpose")))
static const struct { const void *replacement; const void *original; } traversal_hooks[] = {
    { (const void *)observed_srgb, (const void *)cmsCreate_sRGBProfile },
    { (const void *)traversal_transform, (const void *)cmsCreateTransform }
};
