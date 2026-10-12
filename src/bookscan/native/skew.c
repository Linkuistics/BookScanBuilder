/* BookScanBuilder private estimator protocol v1; no image writing or deskew. */
#include <allheaders.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static void number(float value) {
    if (isfinite(value)) printf("%.9g", value);
    else printf("null");
}

int main(int argc, char **argv) {
    /* Preserve sweep warnings; do not let the default severity hide them.
     * https://raw.githubusercontent.com/DanBloomberg/leptonica/1.87.0/src/utils1.c */
    setMsgSeverity(L_SEVERITY_WARNING);
    /* getLeptonicaVersion() returns allocated memory owned by the caller.
     * https://raw.githubusercontent.com/DanBloomberg/leptonica/1.87.0/src/utils1.c */
    char *version = getLeptonicaVersion();
    if (!version) return 5;
    int compatible = !strcmp(version, "leptonica-1.87.0") &&
                     LIBLEPT_MAJOR_VERSION == 1 && LIBLEPT_MINOR_VERSION == 87 &&
                     LIBLEPT_PATCH_VERSION == 0;
    if (!compatible) {
        fprintf(stderr, "unsupported linked/header Leptonica: %s\n", version);
        lept_free(version);
        return 5;
    }
    if (argc == 2 && !strcmp(argv[1], "--identity")) {
        printf("{\"schema\":\"BookScanBuilderSkewIdentity\",\"version\":1,"
               "\"leptonica\":\"%s\",\"headers\":\"1.87.0\"}\n", version);
        lept_free(version);
        return ferror(stdout) ? 5 : 0;
    }
    if (argc != 3 || strcmp(argv[1], "analyze")) {
        fprintf(stderr, "private usage: skew --identity | skew analyze ANALYSIS.png\n");
        lept_free(version);
        return 2;
    }
    PIX *analysis = pixRead(argv[2]);
    if (!analysis || pixGetDepth(analysis) != 8 || pixGetColormap(analysis)) {
        fprintf(stderr, "analysis must be a complete non-colormapped 8-bit image\n");
        pixDestroy(&analysis);
        lept_free(version);
        return 5;
    }
    /* Analysis default 160; never call pixDeskew(), which can apply its threshold.
     * https://raw.githubusercontent.com/DanBloomberg/leptonica/1.87.0/src/skew.c
     * https://raw.githubusercontent.com/DanBloomberg/leptonica/1.87.0/src/grayquant.c */
    PIX *binary = pixThresholdToBinary(analysis, 160);
    if (!binary) {
        pixDestroy(&analysis);
        lept_free(version);
        return 5;
    }
    float angle = 0, ratio = 0;
    /* Explicit pinned defaults; result is deskew degrees, clockwise positive.
     * https://raw.githubusercontent.com/DanBloomberg/leptonica/1.87.0/src/skew.c */
    int status = pixFindSkewSweepAndSearch(binary, &angle, &ratio, 4, 2, 7.0f, 1.0f, 0.01f);
    printf("{\"schema\":\"BookScanBuilderSkew\",\"version\":1,"
           "\"leptonica\":\"%s\",\"width\":%d,\"height\":%d,"
           "\"status\":%d,\"angle_degrees\":", version,
           pixGetWidth(analysis), pixGetHeight(analysis), status);
    number(angle);
    printf(",\"score_ratio\":");
    number(ratio);
    printf("}\n");
    pixDestroy(&binary);
    pixDestroy(&analysis);
    lept_free(version);
    return ferror(stdout) ? 5 : 0;
}
