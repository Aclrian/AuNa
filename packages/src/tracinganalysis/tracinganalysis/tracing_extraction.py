import time
import dataclasses
import json
from tracetools_analysis.processor.ros2 import Ros2DataModel
from tracetools_analysis.loading import load_file

from tracetools_read.trace import *
from dataclasses import dataclass, field
import os
import sys
import re
from typing import Any, Callable, ClassVar, Dict, Hashable, Optional, Protocol, Type, TypeVar, Union

import numpy as np
import pandas as pd

from tracinganalysis.tracetools_analysis_extension import Ros2HandlerWithExtendedTake
from tracinganalysis.code_extraction import ClContext
TRACING_WS_BUILD_PATH = "~/tracing/build/"

# The last few imports can only be resolved using the user-specified paths above
sys.path.append(os.path.join(TRACING_WS_BUILD_PATH, "tracetools_read/"))
sys.path.append(os.path.join(TRACING_WS_BUILD_PATH, "tracetools_analysis/"))


sys.path.append(os.path.join(os.path.expanduser("~"), "workspace", "packages", "src", "ros2_latency_analysis"))
from clang_interop.cl_types import ClContext


@dataclass
class Indexable:
    id: int


@dataclass
class Callbackable(Indexable):
    _store: Optional["TracingStore"]

    @property
    def callback_objects(self) -> Optional[list["CallbackObject"]]:
        if self._store is not None and self.id in self._store.callback_objects:
            return self._store.callback_objects[self.id]
        return None


@dataclass
class CallbackSymbol(Indexable):
    timestamp: int
    symbol: str  # eg. ParameterService(...)


@dataclass
class CallbackInstance(Indexable):
    callback_object: int
    timestamp: pd.Timestamp
    duration: pd.Timedelta
    intra_process: bool


@dataclass
class PublisherInstance(Indexable):
    publisher_handle: np.int64
    timestamp: np.int64
    message: np.int64


@dataclass
class SubscriptionObject(Callbackable):
    timestamp: np.int64
    subscription_handle: np.int64


@dataclass
class TimerNodeLink(Indexable):
    timestamp: np.int64
    node_handle: np.int64


@dataclass
class CallbackObject(Indexable):
    timestamp: np.int64
    callback_object: np.int64
    callback_symbols: List[CallbackSymbol] = field(
        init=False, default_factory=list)
    cached_callback_instances: Optional[pd.DataFrame] = field(init=False, default=None)
    _store: "TracingStore"

    def add_callbacksymbol(self, symbol: CallbackSymbol):
        self.callback_symbols.append(symbol)

    @property
    def callback_instances(self) -> Optional[List[CallbackInstance]]:
        if self.callback_object in self._store.callback_instances_modified:
            return self._store.callback_instances_modified[int(self.callback_object)]
        return None
    
    @property
    def callback_instances_new(self) -> Optional[pd.DataFrame]:
        if self.cached_callback_instances is not None:
            return self.cached_callback_instances
        if self._store.callback_instances is not None:
            if isinstance(self._store.callback_instances, pd.DataFrame):
                select = self._store.callback_instances['callback_object'] == self.callback_object
                self.cached_callback_instances = self._store.callback_instances[select]
                return self.cached_callback_instances
        return None


@dataclass
class Publisher(Indexable):
    timestamp: int
    node_handle: int
    rmw_handle: int
    topic_name: str
    depth: int
    instances: list[PublisherInstance] = field(
        init=False, default_factory=list)
    cached_publish_instances: Optional[pd.DataFrame] = field(init=False, default=None)
    _store: "TracingStore"


    def add_instance(self, instance: PublisherInstance):
        self.instances.append(instance)

    @property
    def publish_instances_new(self) -> Optional[pd.DataFrame]:
        if self.cached_publish_instances is not None:
            return self.cached_publish_instances
        if self._store.publish_instances is not None:
            if isinstance(self._store.publish_instances, pd.DataFrame):
                select = self._store.publish_instances['publisher_handle'] == self.id
                self.cached_publish_instances = self._store.publish_instances[select]
                return self.cached_publish_instances
        return None


@dataclass
class Subscription(Indexable):
    timestamp: int
    node_handle: int
    rmw_handle: int
    topic_name: str
    depth: int
    subscription_objects: list[SubscriptionObject] = field(
        init=False, default_factory=list)

    def add_subscriptionobject(self, subscription_object: SubscriptionObject):
        self.subscription_objects.append(subscription_object)


@dataclass
class Timer(Callbackable):
    timestamp: np.int64
    period: np.int64
    tid: np.int64


@dataclass
class Service(Indexable):
    timestamp: int
    node_handle: int
    service_name: str


@dataclass
class Client(Indexable):
    timestamp: int
    node_handle: int
    service_name: str


@dataclass
class Node(Indexable):
    timestamp: int
    tid: int
    rmw_handle: int
    name: str
    namespace: str
    callbacks: Dict[int, List[Union[Timer, Publisher, Subscription]]
                    ] = field(init=False, default_factory=dict)
    services: List[Service] = field(init=False, default_factory=list)
    clients: List[Client] = field(init=False, default_factory=list)
    c_contexts: List["ClContext"] = field(init=False, default_factory=list)

    def add_callback(self, index: int, callback: Timer | Publisher | Subscription):
        if index in self.callbacks:
            self.callbacks[index].append(callback)
        self.callbacks[index] = [callback]

    def add_service(self, service: Service):
        self.services.append(service)

    def add_client(self, client: Client):
        self.clients.append(client)

    def add_code(self, context: "ClContext"):
        self.c_contexts.append(context)


class DataClassProtocol(Protocol):
    __dataclass_fields__: ClassVar[dict]


T = TypeVar('T', bound=DataClassProtocol)


class TracingStore:
    callback_objects: Dict[int, List[CallbackObject]
                           ] = field(init=False, default_factory=dict)
    callback_instances_modified: Dict[int, List[CallbackInstance]] = field(
        init=False, default_factory=dict)
    nodes: Dict[int, Node] = field(init=False, default_factory=dict)
    callback_instances: Optional[pd.DataFrame]
    publish_instances: Optional[pd.DataFrame]

    def _get_instance(self, dc: Type[T], row: pd.Series, index: Hashable):
        data: dict[str, Any] = {"id": index}
        for field in dc.__dataclass_fields__.values():
            if field.name in row:
                data[field.name] = row[field.name]
            elif not field.init:
                pass
            elif field.name == "_store":
                data[field.name] = self
        return dc(**data)

    def _get_list_from_dataframe(self, dataclass: Type[T], df: pd.DataFrame, skip_if: Callable[[T], bool] = lambda x: False) -> Dict[int, T]:
        data_list = {}
        for index, row in df.iterrows():
            instance = self._get_instance(dataclass, row, index)
            if not skip_if(instance):
                # only CallbackObject, CallbackSymbol, SubscriptionObject and Timer seem to be duplicated. See also: Ros2DataModel:__init__
                # TimerNodeLink also, but duplicates are equal except for timestamp
                data_list[index] = instance
        return data_list

    def _get_list_from_dataframe_with_duplicates(self, dataclass: Type[T], df: pd.DataFrame, skip_if: Callable[[T], bool] = lambda x: False) -> Dict[int, List[T]]:
        data_list = {}
        for index, row in df.iterrows():
            instance = self._get_instance(dataclass, row, index)
            if not skip_if(instance):
                if index in data_list:
                    data_list[index].append(instance)
                else:
                    data_list[index] = [instance]
        return data_list

    def _add_callbacks_to_nodes(self, nodes: Dict[int, Node], cb_dict: Union[Dict[int, Subscription], Dict[int, Publisher]]):
        for key, cb in cb_dict.items():
            try:
                node = nodes[cb.node_handle]
                node.add_callback(key, cb)
            except KeyError:
                pass  # ignore

    def _add_services_to_nodes(self, nodes: Dict[int, Node], services: Dict[int, Service]):
        for key, service in services.items():
            try:
                node = nodes[service.node_handle]
                node.add_service(service)
            except KeyError:
                pass  # ignore

    def _add_clients_to_nodes(self, nodes: Dict[int, Node], clients: Dict[int, List[Client]]):
        for key, c_list in clients.items():
            for client in c_list:
                try:
                    node = nodes[client.node_handle]
                    node.add_client(client)
                except KeyError:
                    pass  # ignore

    def _add_timers_to_nodes(self, nodes: Dict[int, Node], timers: Dict[int, List[Timer]], timer_node_dict: Dict[int, TimerNodeLink]):
        for key, timer_list in timers.items():
            try:
                timer_node_link = timer_node_dict.get(key, None)
                if timer_node_link:
                    node = nodes[int(timer_node_link.node_handle)]
                    for timer in timer_list:
                        node.add_callback(key, timer)
            except KeyError:
                pass  # ignore

    def _add_callbacksymbols_to_callbackobjects(self, syms: Dict[int, List[CallbackSymbol]], objs: Dict[int, List[CallbackObject]]):
        for obj_list in objs.values():
            for obj in obj_list:
                if obj.callback_object not in syms:
                    continue  # ignore
                sym_list = syms[int(obj.callback_object)]
                for sym in sym_list:
                    obj.add_callbacksymbol(sym)

    def _add_callbackinstances_to_callbackobjects(self, cb_inst: Dict[int, CallbackInstance]):
        cb_inst_by_callback_object: Dict[int, List[CallbackInstance]] = dict()
        for cbi in cb_inst.values():
            if cbi.callback_object in cb_inst_by_callback_object:
                cb_inst_by_callback_object[cbi.callback_object].append(cbi)
            else:
                cb_inst_by_callback_object[cbi.callback_object] = [cbi]
        self.callback_instances_modified = cb_inst_by_callback_object

    def _add_publisherinstances_to_publishers(self, instances: Dict[int, PublisherInstance], publishers: Dict[int, Publisher]):
        for inst in instances.values():
            try:
                publishers[int(inst.publisher_handle)].add_instance(inst)
            except KeyError:
                pass  # publisher is in ignore list

    def _add_subscriptionobjects_to_subscriptions(self, sub_objects: Dict[int, List[SubscriptionObject]], subscriptions: Dict[int, Subscription]):
        for sub_obj_list in sub_objects.values():
            for sub_obj in sub_obj_list:
                try:
                    subscriptions[int(sub_obj.subscription_handle)].add_subscriptionobject(
                        sub_obj)
                except KeyError:
                    pass  # ignore

    @classmethod
    def extract(cls, traces: str):
        SKIP_TOPICS = ["/parameter_events", "/rosout", "/clock"]
        SKIP_NODES = ["launch_ros_", r"executor_\d+_container"]
        SKIP_CALLBACK_SYMBOLS = ["ParameterService"]
        SKIP_SERVICE = [".*/get_parameters$", ".*/get_parameter_types$", ".*/set_parameters$",
                        ".*/set_parameters_atomically$", ".*/describe_parameters$", ".*/list_parameters$"]
        # SKIP_SERVICE += [".*/get_available_transitions$", "change_state$", ".*/get_transition_graph$", ".*/get_available_states$", ".*/get_state$", ".*/get_result$", ".*/send_goal$", ".*/cancel_goal$", ".*/is_active$", ".*/namage_nodes"]

        def skip_service(service: Service):
            return any([re.match(pattern, service.service_name) for pattern in SKIP_SERVICE])

        def skip_topics(sub: Union[Subscription, Publisher]):
            return any([re.match(pattern, sub.topic_name) for pattern in SKIP_TOPICS])

        file = load_file(traces)
        handler = Ros2HandlerWithExtendedTake.process(file)
        data_model: Ros2DataModel = handler.data  # type: ignore

        store = TracingStore()
        def log_time_taken(operation_name, start_time):
            end_time = time.time()
            duration = end_time - start_time
            print(f"{str(operation_name)} took {duration:.4f} seconds")
            return time.time()
        
        start = time.time()
        # only CallbackObject, CallbackSymbol, SubscriptionObject and Timer seem to be duplicated. see Ros2DataModel:__init__
        nodes = store._get_list_from_dataframe(Node, data_model.nodes, lambda node: any(
            [re.match(pattern, node.name) for pattern in SKIP_NODES]))
        start_time = log_time_taken("Node", start)
        subscriptions = store._get_list_from_dataframe(
            Subscription, data_model.rcl_subscriptions, skip_topics)
        start_time = log_time_taken("Sub", start_time)
        publishers = store._get_list_from_dataframe(
            Publisher, data_model.rcl_publishers, skip_topics)
        start_time = log_time_taken("Pub", start_time)
        timers = store._get_list_from_dataframe_with_duplicates(
            Timer, data_model.timers)
        start_time = log_time_taken("timers", start_time)
        timer_node_links = store._get_list_from_dataframe(
            TimerNodeLink, data_model.timer_node_links)
        start_time = log_time_taken("tml", start_time)
        subscription_objs = store._get_list_from_dataframe_with_duplicates(
            SubscriptionObject, data_model.subscription_objects)
        start_time = log_time_taken("subo", start_time)
        callback_objects = store._get_list_from_dataframe_with_duplicates(
            CallbackObject, data_model.callback_objects)
        start_time = log_time_taken("cbo", start_time)
        callback_symbols = store._get_list_from_dataframe_with_duplicates(CallbackSymbol, data_model.callback_symbols, lambda cbs: any(
            pattern in cbs.symbol for pattern in SKIP_CALLBACK_SYMBOLS))
        start_time = log_time_taken("cbs", start_time)
        store.publish_instances = data_model.rcl_publish_instances
        #publish_instances = store._get_list_from_dataframe(
        #     PublisherInstance, data_model.rcl_publish_instances)
        start_time = log_time_taken("pubi", start_time)
        store.callback_instances = data_model.callback_instances
        #callback_instances = store._get_list_from_dataframe(
        #    CallbackInstance, data_model.callback_instances)

        start_time = log_time_taken("cbi", start_time)
        clients = store._get_list_from_dataframe_with_duplicates(
            Client, data_model.clients)
        start_time = log_time_taken("client", start_time)
        services = store._get_list_from_dataframe(
            Service, data_model.services, skip_if=skip_service)
        store.callback_objects = callback_objects
        start_time = log_time_taken("service", start_time)
        end =time.time()

        # Node
        store._add_callbacks_to_nodes(nodes, subscriptions)
        start_time = log_time_taken("sub2n", start_time)
        store._add_callbacks_to_nodes(nodes, publishers)
        start_time = log_time_taken("pub2n", start_time)
        store._add_timers_to_nodes(nodes, timers, timer_node_links)
        start_time = log_time_taken("t2n", start_time)
        store._add_services_to_nodes(nodes, services)
        start_time = log_time_taken("s2n", start_time)
        store._add_clients_to_nodes(nodes, clients)
        start_time = log_time_taken("c2n", start_time)

        # Sub and Pub
        store._add_subscriptionobjects_to_subscriptions(
            subscription_objs, subscriptions)
        start_time = log_time_taken("subo2sub", start_time)
        #store._add_publisherinstances_to_publishers(
        #    publish_instances, publishers)
        start_time = log_time_taken("pubi2pub", start_time)

        # CBO
        #store._add_callbackinstances_to_callbackobjects(callback_instances)
        start_time = log_time_taken("cbi2co", start_time)
        store._add_callbacksymbols_to_callbackobjects(
            callback_symbols, callback_objects)
        start_time = log_time_taken("cbs2co", start_time)

        store.nodes = nodes
        end = time.time()

        print("done", end - start)
        return store


if __name__ == "__main__":
    # traces = '~/workspace/traces/new-small-trace/ust'
    traces = '~/workspace/traces/enhanced_tracing/ust'
    # traces = '~/workspace/traces/session-20250913163542/ust' # python

    store = TracingStore.extract(traces)
    print()

# def duration():
#     import math
#     start_time = math.inf
#     end_time = -math.inf
#     for df in [handler.data.nodes, handler.data.rcl_subscriptions, handler.data.rcl_publishers, handler.data.timers, handler.data.timer_node_links, handler.data.subscription_objects, handler.data.callback_objects, handler.data.callback_symbols, handler.data.rcl_publish_instances]:
#         # handler.data.callback_instances
#         earliest = df.min(axis=0)['timestamp']
#         latest = df.max(axis=0)['timestamp']
#         if earliest < start_time:
#             start_time = earliest
#         if latest > end_time:
#             end_time = latest
#     a = datetime.datetime.fromtimestamp(start_time/1e9)
#     b = datetime.datetime.fromtimestamp(end_time/1e9)

#     return b-a


# print(f"Duration of tracing: {duration()}")

# print(callback_instances_modified[[obj for obj_l in callback_objects.keys() for obj in callback_objects[obj_l] if obj.callback_object == 102798063087784][0].callback_object])

# exit(0)
# DONE: TODO: Verbindung timer node
# TODO: Verbindung callback aka: timer, publisher, Subscription zu callback_instances/_obj/_sym
# DONE: TODO: SKIPLIST not working
# TODO: VERBINDUNG subscription, subscriptio_obj/_instance/_symbol
# TODO: Verbindung CB_OBJ zu CB_INST stimmt noch nicht
# TODO: overwork addCallbackObjectToCallbacks
# TODO: verbindung Timer / SubO -> CBO und CBO -> CBI / CBS nicht funktionstüchtig
# Ziel der clang-Analyse:
# - Verbindung callbacks
# - Publisher in welchem callback?
# - read & write Zugriffe in welchem callback?


class Encoding(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, TracingStore):
            raise TypeError("TracingStore instances cannot be serialized")
        if dataclasses.is_dataclass(o):
            result = {}
            for f in dataclasses.fields(o):
                if f.name == "_store":
                    continue
                result[f.name] = getattr(o, f.name)
            return result
        if type(o) == np.int64:
            return int(o)
        if type(o) == pd.Timestamp:
            return o.to_pydatetime().isoformat()
        if type(o) == pd.Timedelta:
            return o / pd.Timedelta(1, "ns")
        return super().default(o)

    def to_file(self, nodes: dict[int, Node], file: str):
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(nodes, f, ensure_ascii=False, indent=4, cls=Encoding)
