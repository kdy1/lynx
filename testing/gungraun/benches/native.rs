use gungraun::prelude::*;
use gungraun::{Bench, BinaryBenchmark, Callgrind, Dhat};
use serde_json::Value;

fn config() -> BinaryBenchmarkConfig {
    let mut config = BinaryBenchmarkConfig::default();
    config.tool(Callgrind::with_args([
        "--cache-sim=yes",
        "--branch-sim=yes",
    ]));
    if std::env::var("LYNX_DHAT").as_deref() == Ok("true") {
        config.tool(Dhat::default());
    }
    config
}

binary_benchmark_group!(
    name = native;
    benchmarks = |group: &mut BinaryBenchmarkGroup| {
        let path = std::env::var("LYNX_CASES").expect("LYNX_CASES");
        let cases: Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
        let mut benchmark = BinaryBenchmark::new("workload");
        for case in cases.as_array().unwrap() {
            let mut command = Command::new(case["binary"].as_str().unwrap());
            command.args(case["args"].as_array().unwrap().iter().map(|v| v.as_str().unwrap()));
            command.current_dir(case["cwd"].as_str().unwrap());
            for (key, value) in case["env"].as_object().unwrap() {
                command.env(key, value.as_str().unwrap());
            }
            let mut bench = Bench::new(case["id"].as_str().unwrap());
            if case["instrumented"].as_bool().unwrap_or(false) {
                bench.config(BinaryBenchmarkConfig::default().tool(Callgrind::with_args([
                    "--cache-sim=yes", "--branch-sim=yes", "--instr-atstart=no",
                ])));
            }
            benchmark.bench(bench.command(command.build()));
        }
        group.binary_benchmark(benchmark);
    }
);
main!(config = config(), binary_benchmark_groups = native);
