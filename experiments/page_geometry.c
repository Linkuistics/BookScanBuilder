/* Disposable Leptonica 1.87 trial. No product API. */
#include <allheaders.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void path(char *dst, const char *dir, const char *name) {
    snprintf(dst, 4096, "%s/%s", dir, name);
}

int main(int argc, char **argv) {
    if (argc != 5) {
        fprintf(stderr, "usage: page_geometry RGB.png ANALYSIS.png OUT_DIR fit|diagnostic\n");
        return 2;
    }
    PIX *input = pixRead(argv[1]), *mask = pixRead(argv[2]);
    if (!input || !mask) return 3;
    PIX *rgb = pixConvertTo32(input), *gray = pixConvertTo8(mask, 0);
    PIX *binary = pixThresholdToBinary(gray, 180);
    int w = pixGetWidth(rgb), h = pixGetHeight(rgb);
    if (pixGetWidth(binary) != w || pixGetHeight(binary) != h) return 4;
    char file[4096];
    path(file, argv[3], "binary.png"); pixWrite(file, binary, IFF_PNG);
    float angle = 0, confidence = 0;
    int skew_status = pixFindSkew(binary, &angle, &confidence);
    PIX *rigid = pixRotateAM(rgb, angle * 3.14159265358979323846 / 180,
                              L_BRING_IN_WHITE);
    path(file, argv[3], "rigid.png"); pixWrite(file, rigid, IFF_PNG);
    PTAA *centres = dewarpGetTextlineCenters(binary, 0);
    PTAA *longlines = centres ? dewarpRemoveShortLines(binary, centres, .8f, 0) : NULL;
    path(file, argv[3], "fitting-lines.json");
    FILE *lines = fopen(file, "w"); if (!lines) return 5;
    fprintf(lines, "[");
    int count = longlines ? ptaaGetCount(longlines) : 0;
    for (int i = 0; i < count; i++) {
        PTA *p = ptaaGetPta(longlines, i, L_CLONE);
        fprintf(lines, "%s[", i ? "," : "");
        for (int j = 0; j < ptaGetCount(p); j++) {
            float x, y; ptaGetPt(p, j, &x, &y);
            fprintf(lines, "%s[%.6g,%.6g]", j ? "," : "", x, y);
        }
        fprintf(lines, "]"); ptaDestroy(&p);
    }
    fprintf(lines, "]\n"); fclose(lines);
    L_DEWARPA *dewa = dewarpaCreate(1, 30, 1, 15, 0);
    dewarpaUseBothArrays(dewa, 0);
    L_DEWARP *dew = dewarpCreate(binary, 0);
    dewarpaInsertDewarp(dewa, dew);
    int diagnostic = !strcmp(argv[4], "diagnostic");
    int build = -1;
    if (diagnostic) {
        /* Declared ahead of output: smooth bounded +/-2.25 px. Square
           full field avoids the library's height-vs-width size check. */
        int side = w > h ? w : h;
        dew->sampvdispar = fpixCreate(2, 2);
        dew->fullvdispar = fpixCreate(side, side);
        for (int y = 0; y < side; y++) for (int x = 0; x < side; x++) {
            float d = 2.25 * sin(2 * 3.14159265358979323846 * x / (w - 1)) *
                      sin(3.14159265358979323846 * y / (h - 1));
            fpixSetPixel(dew->fullvdispar, x, y, d);
        }
        dew->vsuccess = dew->vvalid = 1;
        dewa->modelsready = 1;
    } else {
        build = dewarpBuildPageModel(dew, NULL);
        dewarpaSetValidModels(dewa, 0, 0);
        if (dew->vvalid && dewarpPopulateFullRes(dew, rgb, 0, 0)) return 6;
    }
    int valid = dew->vvalid, success = dew->vsuccess;
    int mincurv = dew->mincurv, maxcurv = dew->maxcurv;
    if (dew->fullvdispar) {
        path(file, argv[3], "field.fpix"); fpixWrite(file, dew->fullvdispar);
        path(file, argv[3], "field.bin");
        FILE *field = fopen(file, "wb"); if (!field) return 7;
        for (int y = 0; y < h; y++) for (int x = 0; x < w; x++) {
            float v; fpixGetPixel(dew->fullvdispar, x, y, &v);
            fwrite(&v, sizeof(v), 1, field);
        }
        fclose(field);
    }
    path(file, argv[3], "model.dew"); dewarpWrite(file, dew);
    PIX *candidate = NULL;
    int apply = valid ? dewarpaApplyDisparity(dewa, 0, rgb, 255, 0, 0,
                                             &candidate, NULL) : -1;
    if (!candidate) candidate = pixClone(rgb);
    path(file, argv[3], "candidate.png"); pixWrite(file, candidate, IFF_PNG);
    path(file, argv[3], "status.json");
    FILE *status = fopen(file, "w"); if (!status) return 8;
    fprintf(status, "{\"leptonica\":\"%s\",\"width\":%d,\"height\":%d,"
        "\"build_return\":%d,\"vsuccess\":%d,\"vvalid\":%d,"
        "\"apply_return\":%d,\"long_line_count\":%d,"
        "\"mincurv\":%d,\"maxcurv\":%d,\"diagnostic\":%d,"
        "\"skew_status\":%d,\"angle_degrees\":%.9g,\"skew_confidence\":%.9g}\n",
        getLeptonicaVersion(), w, h, build, success, valid, apply, count,
        mincurv, maxcurv, diagnostic, skew_status, angle, confidence);
    fclose(status);
    pixDestroy(&candidate); pixDestroy(&rigid); pixDestroy(&binary);
    pixDestroy(&gray); pixDestroy(&rgb); pixDestroy(&input); pixDestroy(&mask);
    ptaaDestroy(&centres); ptaaDestroy(&longlines); dewarpaDestroy(&dewa);
    return 0;
}
