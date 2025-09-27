import os
import sys
from typing import List

from tracinganalysis.tracing_extraction import TracingStore
from tracinganalysis.code_extraction import new_extraction

sys.path.append(os.path.join(os.path.expanduser("~"), "workspace", "packages", "src", "ros2_latency_analysis"))
from clang_interop.cl_types import ClContext

def combine(tracing: TracingStore, contexts: List[ClContext]):
    for t_node in tracing.nodes.values():
        found_match = False
        for code in contexts:
            for c_node in code.nodes:
                if c_node.ros_name and t_node.name.replace("_node", "") == c_node.ros_name.replace("_node", ""):
                    t_node.add_code(code)
                    found_match = True
                    # cannot break here there could be multiple
                    # it seems all data from the static analysis is duplicated?
            if found_match:
                break


if __name__ == "__main__":
    #c_contexts = new_extraction("/home/ubuntu/workspace/packages/src/tracinganalysis/template_system/")
    with open("/home/ubuntu/workspace/packages/src/physical/ros-g29-force-feedback/examples/carla_control.py", "r") as f:
        import ast
        from ast import ClassDef, Name
        code = f.read()
        nodes = []
        ast_f = ast.parse(code)
        for node in ast_f.body:
            if isinstance(node, ClassDef):
                for base in node.bases:
                    if isinstance(base, Name) and base.id == 'Node':
                        nodes.append(node)
    
    c_contexts = new_extraction("/home/ubuntu/workspace/packages/output/")

    #traces = '~/workspace/traces/new-small-trace/ust'
    traces = '~/workspace/traces/session-20250919102136/ust' # actions test
    #traces = '~/workspace/traces/enhanced_tracing/ust'
    #traces = '~/workspace/traces/session-20250913161446/ust'
    #traces = '~/workspace/traces/session-20250913163542/ust' # python
    traces = "/home/ubuntu/workspace/traces/session-20250924192950" # talker listener for presentation

    store = TracingStore.extract(traces)

    combine(store, c_contexts)
    print()
# shortcommings:
# file:///home/aclrian/AuNa/packages/src/auna_tf/src/global_tf/global_tf.cpp#L50
#Subscription(id=103110156010624, timestamp=1756659642084591941, node_handle=103110155372480, rmw_handle=103110156010992, topic_name='/robot1/tf', depth=10, subscription_objects=[SubscriptionObject(id=103110156009728, _store=<tracinganalysis.tracing_extraction.TracingStore object at 0x74bffb99ece0>, timestamp=1756659642085417091, subscription_handle=103110156010624)])
#store.nodes[103110155372480].callbacks[103110156010624][0]