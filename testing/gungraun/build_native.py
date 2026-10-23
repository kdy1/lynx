#!/usr/bin/env python3
"""Build frozen telemetry fixtures against the checked-out production revision."""

from pathlib import Path
import json
import shutil
import subprocess
import sys

source, harness, build = map(Path, sys.argv[1:])
# Only benchmark plumbing is overlaid. Production sources always come from SHA.
shutil.copytree(harness / "telemetry", source / "testing/telemetry", dirs_exist_ok=True)
fixture = source / "testing/gungraun_native"
if fixture.exists():
    shutil.rmtree(fixture)
fixture.mkdir()
for name in ("benchmark_main.cc", "layout_benchmark.cc"):
    shutil.copy2(harness / name, fixture / name)

modules = {
    "layout": ["layout_benchmark.cc"],
    "styling": ["//testing/telemetry/styling/css/selector_matcher_benchmark.cc",
                "//testing/telemetry/styling/css/css_variable_handler_benchmark.cc",
                "//testing/telemetry/styling/css/css_invalidation_benchmark.cc",
                "//testing/telemetry/styling/css/fiber_restyle_benchmark.cc"],
    "runtime": ["//testing/telemetry/lepus/lepus_benchmark.cc"],
}
blocks = []
for name, sources in modules.items():
    blocks.append('''executable("gungraun_%s") {
  testonly = true
  sources = %s
  deps = [
    "//third_party/benchmark:benchmark",
    "//third_party/googletest:gtest",
    "//core/renderer:tasm",
    "//core/renderer/css:css",
    "//core/renderer/dom:dom",
    "//core/renderer/dom:renderer_dom",
    "//core/runtime/lepus/bindings:bindings",
  ]
}
''' % (name, json.dumps(["benchmark_main.cc"] + sources)))
(fixture / "BUILD.gn").write_text('\n'.join(blocks))
subprocess.run(["tools/hab", "sync", "."], cwd=source, check=True)
out = source / "out/gungraun"
if out.exists():
    shutil.rmtree(out)
args = 'enable_unittests=true is_debug=false use_flutter_cxx=false'
root = source / "BUILD.gn"
original = root.read_text()
extra = "".join(f'    "//testing/gungraun_native:gungraun_{name}",\n' for name in modules)
root.write_text(original.replace('  deps = [\n', '  deps = [\n' + extra, 1))
try:
    subprocess.run(["tools/env.sh", "gn", "gen", str(out), "--args=" + args], cwd=source, check=True)
    subprocess.run(["tools/env.sh", "ninja", "-C", str(out), "-j2",
                    *[f"gungraun_{name}" for name in modules]], cwd=source, check=True)
    for name in modules:
        shutil.copy2(out / f"gungraun_{name}", build / f"gungraun_{name}")
finally:
    root.write_text(original)
    subprocess.run(["git", "restore", "--", "testing/telemetry"], cwd=source, check=True)
