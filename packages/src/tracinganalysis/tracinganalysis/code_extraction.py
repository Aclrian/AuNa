import os
import sys


def extract(path: str=os.path.join(os.path.expanduser("~"), "workspace", "packages", "src", "ros2_latency_analysis")):
    sys.path.append(path) #branch dataflow-analysis

    import clang_interop.process_clang_output as pco

    pco.IN_DIR = "/home/ubuntu/workspace/packages/src/tracinganalysis/template_system/"
    pco.SRC_DIR = ""
    print("/home/ubuntu/workspace/packages/src/tracinganalysis/template_system/template_system-src-generic_node.json")
    return pco.process_clang_output()

if __name__ == "__main__":
    clang_context = extract()
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