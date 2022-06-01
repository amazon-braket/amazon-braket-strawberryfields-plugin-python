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

from datetime import datetime
from unittest.mock import Mock

import numpy as np
import pytest

from braket.strawberryfields_plugin import BraketJob

START = datetime(2022, 6, 2, 10, 8, 30, 123)
FINISH = datetime(2022, 6, 2, 10, 8, 59, 100)


@pytest.fixture
def task(result):
    task_mock = Mock()
    task_mock.id = "task_id"
    task_mock.metadata.return_value = {"createdAt": START, "endedAt": FINISH}
    task_mock.result.return_value = result
    task_mock.state.return_value = "COMPLETED"
    task_mock.cancel.return_value = None
    return task_mock


@pytest.fixture
def braket_job(task, sf_device):
    return BraketJob(task, sf_device)


def test_properties(braket_job, task, sf_device):
    assert braket_job.task == task
    assert braket_job.id == task.id
    assert braket_job.target == sf_device.target
    assert braket_job.created_at == START
    assert braket_job.finished_at == FINISH
    runtime = FINISH - START
    assert braket_job.running_time == runtime
    assert braket_job.finished
    assert braket_job.metadata == task.metadata()
    assert braket_job.overview == {
        "id": task.id,
        "status": "complete",
        "target": sf_device.target,
        "created_at": START,
        "finished_at": FINISH,
        "running_time": runtime,
        "metadata": task.metadata(),
    }


def test_incomplete():
    task_mock = Mock()
    task_mock.metadata.return_value = {"createdAt": START}
    job = BraketJob(task_mock, None)
    assert job.finished_at is None
    assert job.running_time is None
    assert not job.finished


@pytest.mark.parametrize(
    "braket_status, sf_status",
    [
        ("CREATED", "open"),
        ("QUEUEING", "open"),
        ("QUEUED", "queued"),
        ("RUNNING", "running"),
        ("COMPLETED", "complete"),
        ("FAILED", "failed"),
        ("CANCELLING", "cancel_pending"),
        ("CANCELLED", "cancelled"),
    ],
)
def test_states(braket_status, sf_status):
    task_mock = Mock()
    task_mock.state.return_value = braket_status
    assert BraketJob(task_mock, None).status == sf_status


def test_result(braket_job, result):
    assert np.allclose(braket_job.result["output"], result.measurements)
    assert braket_job.circuit == result.additional_metadata.xanaduMetadata.compiledProgram


def test_result_none(sf_device):
    task_mock = Mock()
    task_mock.result.return_value = None
    assert BraketJob(task_mock, sf_device).result is None


def test_cancel(braket_job):
    assert braket_job.task.cancel.call_count == 0  # Sanity
    braket_job.cancel()
    assert braket_job.task.cancel.call_count == 1
