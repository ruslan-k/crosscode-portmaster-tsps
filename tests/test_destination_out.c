/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include "gfx/surface.h"

int main(void) {
  unsigned long cases = 0;
  for (int da = 0; da < 256; da++) {
    for (int a = 0; a < 256; a++) {
      for (int c = 0; c < 256; c++) {
        uint8_t expected[4] = {c, (c * 73 + 19) & 255, (c * 17 + 127) & 255, da};
        uint8_t actual[4];
        memcpy(actual, expected, 4);
        blend_pixel_slow(expected, 173, 41, 229, a, OP_DESTINATION_OUT);
        blend_pixel(actual, 173, 41, 229, a, OP_DESTINATION_OUT);
        if (memcmp(actual, expected, 4)) {
          fprintf(stderr, "mismatch da=%d a=%d c=%d: %u,%u,%u,%u vs %u,%u,%u,%u\n",
                  da, a, c, actual[0], actual[1], actual[2], actual[3],
                  expected[0], expected[1], expected[2], expected[3]);
          return 1;
        }
        cases++;
      }
    }
  }
  /* Alpha can round to zero while RGB must remain (the reference tests ao>0). */
  uint8_t tiny[4] = {233, 127, 61, 1};
  blend_pixel(tiny, 0, 0, 0, 254, OP_DESTINATION_OUT);
  assert(tiny[0] == 233 && tiny[1] == 127 && tiny[2] == 61 && tiny[3] == 0);
  printf("PASS destination-out: %lu exhaustive alpha/channel cases\n", cases);
  return 0;
}
