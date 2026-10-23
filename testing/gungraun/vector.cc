// Copyright 2026 The Lynx Authors. All rights reserved.
// Licensed under the Apache License Version 2.0 that can be found in the
// LICENSE file in the root directory of this source tree.

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

#include "base/include/vector.h"

// Each process executes a fixed workload, including setup and destruction.
// The compiler barrier keeps each iteration observable without volatile loads.
template <typename Vector>
uint64_t Run(const char* mode) {
  uint64_t checksum = 0;
  for (int repeat = 0; repeat < 200; ++repeat) {
    Vector values;
    if (std::strcmp(mode, "reserve") == 0) {
      values.reserve(1024);
    }
    for (int i = 0; i < 1024; ++i) {
      values.push_back(static_cast<uint64_t>(i + repeat));
    }
    if (std::strcmp(mode, "erase") == 0) {
      values.erase(values.begin() + 128, values.begin() + 384);
    }
    asm volatile("" : : "r"(values.data()) : "memory");
    for (auto value : values) {
      checksum += value;
    }
  }
  return checksum;
}

int main(int argc, char** argv) {
  if (argc != 2 || (std::strcmp(argv[1], "push") != 0 &&
                    std::strcmp(argv[1], "reserve") != 0 &&
                    std::strcmp(argv[1], "erase") != 0)) {
    return 2;
  }
#ifdef LYNX_GUNGRAUN_REFERENCE
  auto checksum = Run<std::vector<uint64_t>>(argv[1]);
#else
  auto checksum = Run<lynx::base::Vector<uint64_t>>(argv[1]);
#endif
  std::printf("%llu\n", static_cast<unsigned long long>(checksum));
  return 0;
}
