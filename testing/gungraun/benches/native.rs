use gungraun::prelude::*;

#[binary_benchmark]
#[bench::push("push")]
#[bench::reserve("reserve")]
#[bench::erase("erase")]
fn vector(case: &str) -> Command {
    Command::new(std::env::var("LYNX_BENCH_BINARY").expect("LYNX_BENCH_BINARY"))
        .arg(case)
        .build()
}

binary_benchmark_group!(name = native; benchmarks = vector);
main!(binary_benchmark_groups = native);
