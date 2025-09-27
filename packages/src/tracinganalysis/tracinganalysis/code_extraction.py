from dataclasses import dataclass
import json
import os
from subprocess import PIPE, Popen
import sys
from typing import Dict, List, Set

sys.path.append(os.path.join(os.path.expanduser("~"), "workspace", "packages", "src", "ros2_latency_analysis"))
from clang_interop.cl_types import ClField, ClMemberRef, ClMethod, ClNode, ClPublisher, ClSubscription, ClTimer, ClTranslationUnit
from clang_interop.process_clang_output import definitions_from_json, find_data_deps


@dataclass
class ClContext:
    translation_units: 'ClTranslationUnit'

    nodes: Set['ClNode']
    publishers: Set['ClPublisher']
    subscriptions: Set['ClSubscription']
    timers: Set['ClTimer']

    fields: Set['ClField']
    methods: Set['ClMethod']

    accesses: List['ClMemberRef']

    dependencies: Dict['ClMethod', Set['ClMethod']]
    publications: Dict['ClMethod', Set['ClPublisher']]


def new_extraction(input_directory: str):
    unsupressed_stdout = sys.stdout
    sys.stdout = open('/dev/null', 'w')

    contexts = []
    for filename in os.listdir(input_directory):
        print(f"Processing {filename}")
        if not filename.endswith(".json"):
            continue

        with open(os.path.join(input_directory, filename), "r") as f:
            cb_dict = json.load(f)
            if cb_dict is None:
                print(f"  [WARN ] Empty tool output detected in {filename}")
                continue

            tu = ClTranslationUnit(filename)
            
            nodes, pubs, subs, timers, fields, methods, accesses = definitions_from_json(cb_dict, tu)
            deps, publications = find_data_deps(accesses)
            contexts.append(ClContext(tu, nodes, pubs, subs, timers, fields, methods, accesses,
                                    deps, publications))
    sys.stdout = unsupressed_stdout    
    return contexts


def extract(input_dir: str):
    import clang_interop.process_clang_output as pco
    pco.IN_DIR = input_dir
    pco.SRC_DIR = ""
    return pco.process_clang_output()

#if __name__ == "__main__":
#     clang_context = new_extraction("/home/ubuntu/workspace/packages/src/tracinganalysis/template_system/")
#     print(clang_context)
#     bp = Popen('bash -c "source /opt/ros/humble/setup.bash; ros2 trace"', shell=True, stdout=PIPE, stdin=PIPE, stderr=PIPE)
#     a = bp.stdout.readlines()
#     print("")
from subprocess import Popen, PIPE

def start_tracing():
    #bp = Popen('bash -c "source /opt/ros/humble/setup.bash; ros2 trace"', shell=True, stdout=PIPE, stderr=PIPE, stdin=PIPE, text=True)
    bp = Popen('ros2 trace"', shell=True, stdout=PIPE, stderr=PIPE, stdin=PIPE, text=True)

    output_buffer = ""
    while True:
        output = bp.stdout.read(1)
        if output == "" and bp.poll() is not None:
            break
        if output:
            output_buffer += output
            print(output, end='', flush=True)

            if "press enter to start" in output_buffer:
                # start tracing immediately
                bp.stdin.write('\n')
                bp.stdin.flush()
                output_buffer = ""
                break

    stderr_output = bp.stderr.read()
    if stderr_output:
        print(stderr_output.strip())
    return bp


if __name__ == "__main__":
    clang_context = new_extraction("/home/ubuntu/workspace/packages/src/tracinganalysis/template_system/")
    print(clang_context)


"""
Structure:

ClContext:
    translation_units: ClTranslationUnit[];
        filename: string;
    nodes: ClNode[];
        tu: ClTranslationUnit;
        id: number;
        qualified_name: string;
        source_range: ClSourceRange;
        field_ids?: number[];
        method_ids?: number[];
        ros_name?: string;
        ros_namespace?: string;
    publishers: ClPublisher[];
        tu: ClTranslationUnit;
        topic?: string;
        member_id?: number;
        source_range: ClSourceRange;
    subscriptions: ClSubscription[];
        tu: ClTranslationUnit;
        topic?: string;
        callback_id?: number;
        source_range: ClSourceRange;
    timers: ClTimer[];
        tu: ClTranslationUnit;
        callback_id?: number;
        source_range: ClSourceRange;
    fields: ClField[];
        tu: ClTranslationUnit;
        id: number;
        qualified_name: string;
        source_range: ClSourceRange;
    methods: ClMethod[];
        tu: ClTranslationUnit;
        id: number;
        qualified_name: string;
        source_range: ClSourceRange;
        return_type?: string;
        parameter_types?: string[];
        is_lambda?: boolean;
    accesses: ClMemberRef[];
        tu: ClTranslationUnit;
        type?: "read" | "write" | "call" | "arg" | "pub";
        member_chain: number[];
        method_id?: number;
        node_id?: number;
        source_range: ClSourceRange;
    dependencies: Record<ClMethod, Set<ClMethod>>;
    publications: Record<ClMethod, Set<ClPublisher>>;
}

"""