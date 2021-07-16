/*
 FFT and convolution test (C)

 Copyright (c) 2020 Project Nayuki. (MIT License)
 https://www.nayuki.io/page/free-small-fft-in-multiple-languages

 Permission is hereby granted, free of charge, to any person obtaining a copy of
 this software and associated documentation files (the "Software"), to deal in
 the Software without restriction, including without limitation the rights to
 use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:
 - The above copyright notice and this permission notice shall be included in
   all copies or substantial portions of the Software.
 - The Software is provided "as is", without warranty of any kind, express or
   implied, including but not limited to the warranties of merchantability,
   fitness for a particular purpose and noninfringement. In no event shall the
   authors or copyright holders be liable for any claim, damages or other
   liability, whether in an action of contract, tort or otherwise, arising from,
   out of or in connection with the Software or the use or other dealings
   in the Software.
*/

#include <math.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "fft-real-pair.h"


// Private function prototypes
static void test_fft(int n);
static void naive_dft(const float *inreal, const float *inimag,
    float *outreal, float *outimag, int n, bool inverse);
static void naive_convolve(const float *xreal, const float *ximag,
    const float *yreal, const float *yimag,
    float *outreal, float *outimag, int n);
static float log10_rms_err(const float *xreal, const float *ximag,
    const float *yreal, const float *yimag, int n);
static float *random_reals(int n);
static void *memdup(const void *src, size_t n);

static float max_log_error = -INFINITY;


/*---- Main and test functions ----*/

int main(void) {
    srand(time(NULL));

    // Test power-of-2 size FFTs
    for (int i = 1; i <= 9; i++)
        test_fft(1 << i);

    printf("\n");
    printf("Max log err = %.1f\n", max_log_error);
    printf("Test %s\n", max_log_error < -5 ? "passed" : "failed");
    return EXIT_SUCCESS;
}


static void test_fft(int n) {
    float *inputreal = random_reals(n);
    float *inputimag = random_reals(n);

    float *expectreal = malloc(n * sizeof(float));
    float *expectimag = malloc(n * sizeof(float));
    naive_dft(inputreal, inputimag, expectreal, expectimag, n, false);

    float *actualreal = memdup(inputreal, n * sizeof(float));
    float *actualimag = memdup(inputimag, n * sizeof(float));
    Fft_transform(actualreal, actualimag, n);
    float err0 = log10_rms_err(expectreal, expectimag, actualreal,
                                actualimag, n);

    for (int i = 0; i < n; i++) {
        actualreal[i] /= n;
        actualimag[i] /= n;
    }
    Fft_inverseTransform(actualreal, actualimag, n);
    float err1 = log10_rms_err(inputreal, inputimag,
                                actualreal, actualimag, n);
    printf("fftsize=%4d  logerr=%5.1f\n", n, (err0 > err1 ? err0 : err1));

    free(inputreal);
    free(inputimag);
    free(expectreal);
    free(expectimag);
    free(actualreal);
    free(actualimag);
}



/*---- Naive reference computation functions ----*/

static void naive_dft(const float *inreal, const float *inimag,
        float *outreal, float *outimag, int n, bool inverse) {

    float coef = (inverse ? 2 : -2) * M_PI;
    for (int k = 0; k < n; k++) {  // For each output element
        float sumreal = 0;
        float sumimag = 0;
        for (int t = 0; t < n; t++) {  // For each input element
            float angle = coef * ((long long)t * k % n) / n;
            sumreal += inreal[t] * cos(angle) - inimag[t] * sin(angle);
            sumimag += inreal[t] * sin(angle) + inimag[t] * cos(angle);
        }
        outreal[k] = sumreal;
        outimag[k] = sumimag;
    }
}


static void naive_convolve(const float *xreal, const float *ximag,
        const float *yreal, const float *yimag,
        float *outreal, float *outimag, int n) {

    for (int i = 0; i < n; i++) {
        outreal[i] = 0;
        outimag[i] = 0;
    }
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int k = (i + j) % n;
            outreal[k] += xreal[i] * yreal[j] - ximag[i] * yimag[j];
            outimag[k] += xreal[i] * yimag[j] + ximag[i] * yreal[j];
        }
    }
}


/*---- Utility functions ----*/

static float log10_rms_err(const float *xreal, const float *ximag,
        const float *yreal, const float *yimag, int n) {

    float err = pow(10, -99 * 2);
    for (int i = 0; i < n; i++) {
        float real = xreal[i] - yreal[i];
        float imag = ximag[i] - yimag[i];
        err += real * real + imag * imag;
    }

    err /= n > 0 ? n : 1;
    err = sqrt(err);  // Now this is a root mean square (RMS) error
    err = log10(err);
    if (err > max_log_error)
        max_log_error = err;
    return err;
}


static float *random_reals(int n) {
    float *result = malloc(n * sizeof(float));
    for (int i = 0; i < n; i++)
        result[i] = (rand() / (RAND_MAX + 1.0)) * 2 - 1;
    return result;
}


static void *memdup(const void *src, size_t n) {
    void *dest = malloc(n);
    if (n > 0 && dest != NULL)
        memcpy(dest, src, n);
    return dest;
}
