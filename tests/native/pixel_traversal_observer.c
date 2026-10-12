/* Actual renderer child only. Preserve all earlier observers by inclusion. */
#define __attribute__(x)
#include "lut_traversal_observer.c"
#undef __attribute__

typedef struct {
    _cmsTRANSFORM *transform;
    _cmsTransform2Fn worker;
    unsigned seq, calls;
} PixelState;

static PixelState pixel_states[8], *pixel_active;
static unsigned pixel_states_count, pixel_index, pixel_pending;
static cmsFormatter16 pixel_from, pixel_to;
static FILE *pixel_file;
static const unsigned char *pixel_input;
static unsigned char *pixel_output;
static cmsUInt32Number pixel_width, pixel_line_in, pixel_line_out;

static cmsUInt8Number *pixel_input_format(struct _cmstransform_struct *p,
        cmsUInt16Number values[], cmsUInt8Number *buffer, cmsUInt32Number stride) {
    if (!pixel_active || p != pixel_active->transform || pixel_pending) _exit(170);
    size_t offset = (pixel_index / pixel_width) * pixel_line_in + (pixel_index % pixel_width)*3;
    if (buffer != pixel_input + offset) _exit(171);
    memset(trace_row, 0, sizeof(trace_row));
    trace_row[0] = pixel_index;
    for (unsigned c = 0; c < 3; c++) trace_row[1+c] = buffer[c];
    cmsUInt8Number *next = pixel_from(p, values, buffer, stride);
    if (next != buffer + 3) _exit(172);
    for (unsigned c = 0; c < 3; c++) trace_row[4+c] = values[c];
    for (unsigned c = 3; c < cmsMAXCHANNELS; c++) if (values[c]) _exit(173);
    trace_phase = trace_calls = trace_stage_calls = 0;
    pixel_pending = 1;
    return next;
}

static cmsUInt8Number *pixel_output_format(struct _cmstransform_struct *p,
        cmsUInt16Number values[], cmsUInt8Number *buffer, cmsUInt32Number stride) {
    if (!pixel_active || p != pixel_active->transform || !pixel_pending) _exit(174);
    size_t offset = (pixel_index / pixel_width) * pixel_line_out + (pixel_index % pixel_width)*3;
    if (buffer != pixel_output + offset || trace_calls > 1
        || trace_stage_calls != 3*trace_calls || trace_phase != 3*trace_calls) _exit(175);
    for (unsigned c = 0; c < 3; c++) trace_row[25+c] = values[c];
    for (unsigned c = 3; c < cmsMAXCHANNELS; c++) if (values[c]) _exit(173);
    cmsUInt8Number *next = pixel_to(p, values, buffer, stride);
    if (next != buffer + 3) _exit(176);
    for (unsigned c = 0; c < 3; c++) trace_row[28+c] = buffer[c];
    trace_row[31] = trace_calls;
    trace_row[32] = trace_stage_calls;
    trace_row[33] = trace_calls == 0;
#ifdef BOOKSCAN_TEST_WRONG_PIXEL_OUTPUT
    trace_row[28] ^= 2;
#endif
    if (fwrite(trace_row, sizeof(trace_row), 1, pixel_file) != 1) _exit(177);
    pixel_index++;
    pixel_pending = 0;
    return next;
}

static void pixel_binding(FILE *file, const char *role, const void *pointer) {
    Dl_info info;
    if (!dladdr(pointer, &info) || !info.dli_fname || !info.dli_fbase) _exit(178);
    fprintf(file, "%s %" PRIuPTR " %" PRIuPTR "\n%s\n", role,
            (uintptr_t)pointer, (uintptr_t)info.dli_fbase, info.dli_fname);
}

static void pixel_worker(struct _cmstransform_struct *p, const void *in, void *out,
        cmsUInt32Number width, cmsUInt32Number lines, const cmsStride *stride) {
    /* CachedXFORM copies p->Cache per call; capture real formatter/LUT callbacks.
       The wrapper observes original arguments and restores entire structs.
       https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmsxform.c */
    if (pixel_active || !width || !lines || width > 1000000/lines) _exit(179);
    PixelState *state = NULL;
    for (unsigned i = 0; i < pixel_states_count; i++)
        if (pixel_states[i].transform == p) state = pixel_states+i;
    size_t cache_offset = offsetof(_cmsTRANSFORM, Cache);
#ifdef BOOKSCAN_TEST_WRONG_PIXEL_ABI
    cache_offset += 8;
#endif
    if (!state || p->xform != pixel_worker || !p->Lut || p->Lut->Data != p->Lut
        || cache_offset != 48 || offsetof(_cmsTRANSFORM, FromInput) != 16
        || offsetof(_cmsTRANSFORM, ToOutput) != 24 || offsetof(_cmsTRANSFORM, xform) != 8)
        _exit(180);
    char suffix[128];
    unsigned call = ++state->calls;
    snprintf(suffix, sizeof(suffix), "pixels-%u.txt", call);
    FILE *header = reserve(state->seq, suffix);
    fprintf(header, "pixels-v1 %d %u %u %" PRIuPTR " %" PRIuPTR " %u %u %u %u %u %u %u %u\n",
            getpid(), state->seq, call, (uintptr_t)p, (uintptr_t)p->Lut,
            p->InputFormat, p->OutputFormat, width, lines, stride->BytesPerLineIn,
            stride->BytesPerLineOut, stride->BytesPerPlaneIn, stride->BytesPerPlaneOut);
    pixel_binding(header, "worker", (const void *)state->worker);
    pixel_binding(header, "input", (const void *)p->FromInput);
    pixel_binding(header, "output", (const void *)p->ToOutput);
    fprintf(header, "seed");
    for (unsigned c = 0; c < cmsMAXCHANNELS; c++) fprintf(header, " %u", p->Cache.CacheIn[c]);
    for (unsigned c = 0; c < cmsMAXCHANNELS; c++) fprintf(header, " %u", p->Cache.CacheOut[c]);
    fprintf(header, "\n");
    snprintf(suffix, sizeof(suffix), "pixels-%u.bin", call);
    pixel_file = reserve(state->seq, suffix);
    p->xform = state->worker;
    _cmsTRANSFORM saved_transform;
    cmsPipeline saved_lut;
    cmsStage saved_stages[3];
    memcpy(&saved_transform, p, sizeof(*p));
    trace_lut = p->Lut;
    memcpy(&saved_lut, trace_lut, sizeof(saved_lut));
    trace_eval16 = trace_lut->Eval16Fn;
    cmsStage *stage = trace_lut->Elements;
    for (unsigned s = 0; s < 3; s++) {
        if (!stage || !stage->EvalPtr) _exit(181);
        trace_stages[s] = stage;
        memcpy(saved_stages+s, stage, sizeof(*stage));
        trace_original[s] = stage->EvalPtr;
        stage->EvalPtr = trace_stage;
        stage = stage->Next;
    }
    if (stage) _exit(181);
    trace_lut->Eval16Fn = trace_pipeline;
    pixel_from = p->FromInput; pixel_to = p->ToOutput;
    p->FromInput = pixel_input_format; p->ToOutput = pixel_output_format;
    pixel_active = state; pixel_index = pixel_pending = 0;
    pixel_input = in; pixel_output = out; pixel_width = width;
    pixel_line_in = stride->BytesPerLineIn; pixel_line_out = stride->BytesPerLineOut;
    state->worker(p, in, out, width, lines, stride);
    if (pixel_pending || pixel_index != width*lines) _exit(182);
    for (unsigned s = 0; s < 3; s++) {
        trace_stages[s]->EvalPtr = trace_original[s];
        if (memcmp(trace_stages[s], saved_stages+s, sizeof(cmsStage))) _exit(183);
    }
    trace_lut->Eval16Fn = trace_eval16;
    p->FromInput = pixel_from; p->ToOutput = pixel_to;
    if (memcmp(trace_lut, &saved_lut, sizeof(saved_lut))
        || memcmp(p, &saved_transform, sizeof(*p))) _exit(183);
    fprintf(header, "complete %u restored 1\n", pixel_index);
    if (ferror(pixel_file) || fclose(pixel_file) || ferror(header) || fclose(header)) _exit(184);
    pixel_active = NULL; trace_lut = NULL;
    p->xform = pixel_worker;
}

static cmsHTRANSFORM pixel_transform(cmsHPROFILE input, cmsUInt32Number in,
        cmsHPROFILE target, cmsUInt32Number out, cmsUInt32Number intent, cmsUInt32Number flags) {
    (void)traversal_hooks;
    cmsHTRANSFORM result = traversal_transform(input, in, target, out, intent, flags);
    if ((in == 262169 || in == 25) && out == 262169) {
        if (pixel_states_count == 8) _exit(185);
        PixelState *state = pixel_states + pixel_states_count++;
        state->transform = result; state->worker = state->transform->xform;
        state->seq = atomic_load(&sequence);
        state->transform->xform = pixel_worker;
    }
    return result;
}

__attribute__((used, section("__DATA,__interpose")))
static const struct { const void *replacement; const void *original; } pixel_hooks[] = {
    { (const void *)observed_srgb, (const void *)cmsCreate_sRGBProfile },
    { (const void *)pixel_transform, (const void *)cmsCreateTransform }
};
