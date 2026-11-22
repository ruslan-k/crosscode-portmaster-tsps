/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "gfx/surface.h"

/* quixjs 0.2.2 source-over oracle, kept in its original unspecialized form. */
static void original_source_over(uint8_t *dst, int r, int g, int b, int a) {
  if (a <= 0) return;
  if (a >= 255 || dst[3] == 0) {
    dst[0] = r; dst[1] = g; dst[2] = b; dst[3] = a;
    return;
  }
  int da = dst[3];
  int oa = a * 255 + da * (255 - a);
  int k = da * (255 - a) / 255;
  dst[0] = (r * a + dst[0] * k) * 255 / oa;
  dst[1] = (g * a + dst[1] * k) * 255 / oa;
  dst[2] = (b * a + dst[2] * k) * 255 / oa;
  dst[3] = (oa + 127) / 255;
}

int main(void) {
  unsigned long cases = 0;
  for (int a = 0; a < 256; a++) {
    for (int src = 0; src < 256; src++) {
      for (int dst = 0; dst < 256; dst++) {
        uint8_t expected[4] = {dst, (dst * 73 + 19) & 255, (dst * 17 + 127) & 255, 255};
        uint8_t actual[4];
        memcpy(actual, expected, 4);
        int sr = src, sg = (src * 41 + 23) & 255, sb = (src * 97 + 71) & 255;
        original_source_over(expected, sr, sg, sb, a);
        blend_pixel(actual, sr, sg, sb, a, OP_SOURCE_OVER);
        if (memcmp(actual, expected, 4)) {
          fprintf(stderr, "mismatch a=%d src=%d dst=%d\n", a, src, dst);
          return 1;
        }
        cases++;
      }
    }
  }
  puts("PASS source-over opaque destination: 16777216 alpha/source/destination cases");
  assert(cases == 16777216);
  return 0;
}
