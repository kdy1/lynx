// Copyright 2026 The Lynx Authors. All rights reserved.
// Licensed under the Apache License Version 2.0 that can be found in the
// LICENSE file in the root directory of this source tree.

// GN release builds define NVALGRIND; this runner needs client requests.
#ifdef NVALGRIND
#undef NVALGRIND
#endif

#include <cstdio>
#include <vector>

#include "base/include/log/logging.h"
#include "third_party/benchmark/include/benchmark/benchmark.h"
#include "third_party/googletest/googletest/include/gtest/gtest.h"
#include "valgrind/callgrind.h"

// Suppress clock-dependent formatting. The suite selects exactly one case and
// --benchmark_min_time=0 makes the pinned Benchmark runner execute it once.
class ValidationReporter : public benchmark::BenchmarkReporter {
 public:
  bool ReportContext(const Context&) override {
    CALLGRIND_START_INSTRUMENTATION;
    return true;
  }
  void ReportRuns(const std::vector<Run>& reports) override {
    CALLGRIND_STOP_INSTRUMENTATION;
    for (const auto& report : reports) {
      if (report.error_occurred) {
        std::fprintf(stderr, "%s\n", report.error_message.c_str());
      }
      ++runs;
      valid = valid && !report.error_occurred && report.iterations == 1;
    }
  }
  int runs = 0;
  bool valid = true;
};

void BenchmarkLog(lynx::base::logging::LogMessage* message, const char*) {
  if (message->severity() == lynx::base::logging::LOG_FATAL) {
    std::fprintf(stderr, "%s", message->stream().str().c_str());
  }
}

int main(int argc, char** argv) {
  // The public threshold keeps ERROR enabled. Route diagnostics through a quiet
  // callback instead of the fallback console sink; fatal messages still abort.
  lynx::base::logging::SetMinLogLevel(lynx::base::logging::LOG_ERROR);
  lynx::base::logging::InitLynxLogging(nullptr, BenchmarkLog, true);
  benchmark::Initialize(&argc, argv);
  if (benchmark::ReportUnrecognizedArguments(argc, argv)) return 2;
  ValidationReporter reporter;
  benchmark::RunSpecifiedBenchmarks(&reporter);
  if (!reporter.valid || reporter.runs != 1 ||
      ::testing::UnitTest::GetInstance()->Failed()) return 3;
  std::puts("ok");
  return 0;
}
