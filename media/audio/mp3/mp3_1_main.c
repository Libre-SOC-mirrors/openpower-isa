#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// win 40 floats, in 18 floats, buf 1152 floats, out 2304 floats
void imdct36(float *out, float *buf, float *in, const float *win);

static void readfile(const char name[], void *buf, const unsigned len) {
	FILE *f = fopen(name, "r");
	if (!f) {
        printf("No file %s\n", name);
		exit(1);
    }
	if (fread(buf, len, 1, f) != 1)
		exit(1);
	fclose(f);
}

int main() {
	float win[40], in[18], buf[1152], out[2304] = { 0 }, outexp[2304];

	int i;
	for (i = 0; i < 24; i++) {
		char name[32];

		sprintf(name, "win%u", i);
		readfile(name, win, 40 * 4);

		sprintf(name, "buf%u", i);
		readfile(name, buf, 1152 * 4);

		sprintf(name, "in%u", i);
		readfile(name, in, 18 * 4);

		sprintf(name, "out%u", i);
		readfile(name, outexp, 2304 * 4);

		sprintf(name, "beforeout%u", i);
		readfile(name, out, 2304 * 4);

		imdct36(out, buf, in, win);

		if (memcmp(out, outexp, 2304 * 4)) {
			printf("Failed at %u\n", i);
			FILE *f = fopen("/tmp/fail", "w");
			fwrite(out, 2304 * 4, 1, f);
			fclose(f);
			return 1;
		}
	}

	puts("ok");
	return 0;
}
