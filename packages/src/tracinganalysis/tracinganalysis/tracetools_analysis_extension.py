from typing import Dict
from tracetools_analysis.processor.ros2 import Ros2Handler, Ros2DataModel
from tracetools_analysis.processor import EventMetadata
from tracetools_read import get_field


class Ros2DataModelWithExtendedTake(Ros2DataModel):

    def add_rcl_take_instance(
        self, timestamp, message, node, pid
    ) -> None:
        self._rcl_take_instances.append({
            'timestamp': timestamp,
            'message': message,
            'node': node,
            'pid': pid,
        })


class Ros2HandlerWithExtendedTake(Ros2Handler):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # overwrite data model to add more information to rcl_take_instances
        self._data_model = Ros2DataModelWithExtendedTake()

    def _handle_rcl_take(self, event: Dict, metadata: EventMetadata) -> None:
        timestamp = metadata.timestamp
        message = get_field(event, 'message')
        node = metadata.procname
        pid = metadata.pid
        self._data_model.add_rcl_take_instance(timestamp, message, node, pid)
