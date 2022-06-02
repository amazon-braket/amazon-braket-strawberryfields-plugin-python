# Copyright Amazon.com Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from datetime import datetime, timedelta
from typing import Any, List, Mapping, Optional, Union

import numpy as np
import strawberryfields as sf
from braket.aws import AwsQuantumTask
from braket.tasks import PhotonicModelQuantumTaskResult

_STATE_MAP = {
    "CREATED": "open",
    "QUEUEING": "open",
    "QUEUED": "queued",
    "RUNNING": "running",
    "COMPLETED": "complete",
    "FAILED": "failed",
    "CANCELLING": "cancel_pending",
    "CANCELLED": "cancelled",
}
_TERMINAL_STATES = frozenset({"COMPLETED", "FAILED", "CANCELLED"})


class BraketJob:
    """Wraps an Amazon Braket task to be compatible with the xcc.Job API.

    Args:
        task (AwsQuantumTask): The underlying Braket task
    """

    def __init__(self, task: AwsQuantumTask, device: sf.Device):
        self._task = task
        self._device = device

    @property
    def task(self):
        """AwsQuantumTask: The underling Braket quantum task."""
        return self._task

    @property
    def id(self) -> str:
        """str: The ID of the underlying Braket task."""
        return self._task.id

    @property
    def status(self) -> str:
        """str: The status of the job.

        This is the XCC status corresponding to the underlying Braket task's status
        """
        return _STATE_MAP[self._task.state()]

    @property
    def target(self) -> str:
        """str: The target device"""
        return self._device.target

    @property
    def overview(self) -> Mapping[str, Any]:
        """Mapping[str, Any]: mapping from field names to values for this job.

        Includes the fields "id", "status", "target", "language", "created_at",
        "finished_at", "running_time", and "metadata".
        """
        return {
            "id": self.id,
            "status": self.status,
            "target": self.target,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "running_time": self.running_time,
            "metadata": self.metadata,
        }

    @property
    def created_at(self) -> datetime:
        """datetime: The time at which the job was created."""
        return self._task.metadata()["createdAt"]

    @property
    def finished_at(self) -> Optional[datetime]:
        """Optional[datetime]: The time at which the job completed.

        Returns None if the job is not completed yet.
        """
        return self._task.metadata().get("endedAt")

    @property
    def running_time(self) -> Optional[timedelta]:
        """Optional[timedelta]: The total runtime of the job, from creation to completion.

        Returns None if the job is not completed yet.
        """
        finished_at = self.finished_at
        return finished_at - self.created_at if finished_at else None

    @property
    def finished(self) -> bool:
        """bool: Whether the task is in a terminal state, namely {COMPLETED, CANCELLED, FAILED}"""
        return self._task.state() in _TERMINAL_STATES

    @property
    def circuit(self) -> str:
        """str: The compiled Blackbird circuit that was run for this job.

        Notes:
            This is only available after the underlying task is completed.
        """
        return self._task.result().additional_metadata.xanaduMetadata.compiledProgram

    @property
    def metadata(self) -> Mapping[str, Any]:
        """Mapping[str, Any]: The Braket metadata associated with the underlying task."""
        return self._task.metadata()

    @property
    def result(self) -> Optional[Mapping[str, Union[np.ndarray, List[np.ndarray]]]]:
        """Optional[Mapping[str, Union[np.ndarray, List[np.ndarray]]]]: The result of the job.

        The dict has an "output" key associated with a list of NumPy arrays representing
        the output of the job. Returns ``None`` if the job failed or timed out.
        """
        task_result: PhotonicModelQuantumTaskResult = self._task.result()
        return {"output": [task_result.measurements]} if task_result else None

    def cancel(self) -> None:
        """Cancel the underlying Braket task."""
        self._task.cancel()
