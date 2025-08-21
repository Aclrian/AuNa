#!/bin/bash
# MIT License

# Copyright (c) 2023 TUM - Autonomous Vehicle Systems Lab

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# original: https://github.com/TUM-AVS/ros2_latency_analysis/tree/code-analysis
# differences: 
# - --extra-arg=-std=c++17
# - find $source_dir -type f -name "*.cpp" ! -name "*main.cpp"

if [ -z $1 ]; then
    echo "Usage: $0 </path/to/ros/workspace>"
    exit 1
fi

cur_dir=$PWD
ros_project_dir=$1

source_dir="$ros_project_dir/src"
build_dir="$ros_project_dir/build"

out_dir="$cur_dir/output"
mkdir -p $out_dir

node_tus=$(find $source_dir -type f -name "*.cpp" ! -name "*main.cpp" )
total_tus=$(find $source_dir -type f -name "*.cpp" ! -name "*main.cpp"  | wc -l)

worker_task() {
  my_j=$1
  source_dir=$2
  build_dir=$3
  out_dir=$4
  node_tu=$5

  rel_name=$(realpath --relative-to $source_dir $node_tu)
  json_name=${rel_name//\//-}
  json_name=${json_name//'.cpp'/'.json'}

  echo "$my_j/$total_tus $rel_name"

  tu_in_db=$(cat $build_dir/compile_commands.json | grep "$node_tu")
  if [ -z "$tu_in_db" ]; then
    echo -e "  \e[31mFile not found in compile DB: $(realpath --relative-to $source_dir $node_tu)\e[0m"
    echo "null" >"$out_dir/$json_name"
  else
    echo "./dep-check --extra-arg=-w --extra-arg=-std=c++17 -o "$out_dir/$json_name" -p $build_dir $node_tu >/dev/null"
    ./dep-check --extra-arg=-w --extra-arg=-std=c++17 -o "$out_dir/$json_name" -p $build_dir $node_tu >/dev/null
  fi
}

N=8
i=0
j=0
(
  for node_tu in $node_tus; do
    ((j++))
    ((i = i % N))
    ((i++ == 0)) && wait
    worker_task $j $source_dir $build_dir $out_dir $node_tu &
  done
)

echo "Done."