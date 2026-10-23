// Copyright 2026 The Lynx Authors. All rights reserved.
// Licensed under the Apache License Version 2.0 that can be found in the
// LICENSE file in the root directory of this source tree.

#include <cmath>
#include <memory>
#include <vector>

#include "core/renderer/css/computed_css_style.h"
#include "core/renderer/starlight/layout/layout_object.h"
#include "third_party/benchmark/include/benchmark/benchmark.h"

namespace lynx {
namespace starlight {
namespace {

void BM_Layout(benchmark::State& state, DisplayType display, bool cached) {
  LayoutConfigs config;
  config.SetQuirksMode(base::Version(3, 1));
  std::vector<std::unique_ptr<ComputedCSSStyle>> styles;
  std::vector<std::unique_ptr<LayoutObject>> nodes;
  auto create = [&](float width, float height) {
    styles.push_back(std::make_unique<ComputedCSSStyle>(1.f, 1.f));
    auto* style = styles.back()->GetLayoutComputedStyle();
    style->SetWidth(NLength::MakeUnitNLength(width));
    style->SetHeight(NLength::MakeUnitNLength(height));
    nodes.push_back(std::make_unique<LayoutObject>(config, style));
    return nodes.back().get();
  };
  auto* root = create(1024, 1024);
  auto* style = root->GetCSSMutableStyle();
  style->SetDisplay(display);
  if (display == DisplayType::kGrid) {
    for (int i = 0; i < 8; ++i) {
      auto* grid = style->grid_data_.Access();
      grid->grid_template_columns_min_track_sizing_function_.push_back(
          NLength::MakeUnitNLength(128));
      grid->grid_template_columns_max_track_sizing_function_.push_back(
          NLength::MakeUnitNLength(128));
      grid->grid_template_rows_min_track_sizing_function_.push_back(
          NLength::MakeUnitNLength(128));
      grid->grid_template_rows_max_track_sizing_function_.push_back(
          NLength::MakeUnitNLength(128));
    }
  }
  for (int i = 0; i < 64; ++i) root->AppendChild(create(16, 16));
  root->ReLayout();
  for (auto _ : state) {
    for (int i = 0; i < 100; ++i) {
      if (!cached) root->MarkDirtyRecursion();
      root->ReLayout();
      benchmark::DoNotOptimize(root->GetBorderBoundWidth());
    }
  }
  if (root->GetBorderBoundWidth() != 1024 ||
      root->GetBorderBoundHeight() != 1024 || root->GetChildCount() != 64) {
    state.SkipWithError("Invalid root geometry");
  }
  for (size_t i = 1; i < nodes.size(); ++i) {
    if (!std::isfinite(nodes[i]->GetBorderBoundWidth()) ||
        nodes[i]->GetBorderBoundWidth() <= 0 ||
        nodes[i]->GetBorderBoundHeight() != 16) {
      state.SkipWithError("Invalid child geometry");
    }
  }
  // ContainerNode does not own the children. Detach before destroying them.
  for (size_t i = 1; i < nodes.size(); ++i) root->RemoveChild(nodes[i].get());
}

BENCHMARK_CAPTURE(BM_Layout, Flex, DisplayType::kFlex, false);
BENCHMARK_CAPTURE(BM_Layout, Grid, DisplayType::kGrid, false);
BENCHMARK_CAPTURE(BM_Layout, CachedFlex, DisplayType::kFlex, true);

}  // namespace
}  // namespace starlight
}  // namespace lynx
