#!/bin/zsh
set -eu
here=${0:A:h}
cd "$here"
cargo test --quiet
cargo run --quiet --release -- --convergence-test
