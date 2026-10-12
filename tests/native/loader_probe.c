/* Test-owned post-launch dlopen; no static link to the selected leaf. */
#include <dlfcn.h>
#include <stdio.h>

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    void *library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (library == NULL) { fprintf(stderr, "%s\n", dlerror()); return 3; }
    int (*value)(void) = (int (*)(void))dlsym(library, "bookscan_leaf_value");
    if (value == NULL) { dlclose(library); return 4; }
    printf("%d\n", value());
    return dlclose(library) == 0 ? 0 : 5;
}
