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

from unittest.mock import Mock, patch

import numpy as np
import pytest
import strawberryfields as sf
from braket.aws import AwsQuantumTask
from braket.device_schema.simulators import GateModelSimulatorDeviceCapabilities
from braket.device_schema.xanadu import XanaduDeviceCapabilities
from braket.ir.blackbird import Program
from strawberryfields import ops
from strawberryfields.tdm import borealis_gbs, get_mode_indices

from braket.strawberryfields_plugin import BraketEngine


@pytest.fixture
def device_capabilities(service_properties, action, paradigm_properties, provider_properties):
    return XanaduDeviceCapabilities.parse_obj(
        {
            "braketSchemaHeader": {
                "name": "braket.device_schema.xanadu.xanadu_device_capabilities",
                "version": "1",
            },
            "service": service_properties,
            "action": action,
            "paradigm": paradigm_properties,
            "provider": provider_properties,
            "deviceParameters": {},
        }
    )


@pytest.fixture
@patch("braket.strawberryfields_plugin.braket_engine.AwsDevice")
def braket_engine(mock_qpu, device_capabilities, device_arn, s3_destination_folder):
    mock_qpu.return_value.properties = device_capabilities
    mock_qpu.return_value.run.return_value = Mock()
    return BraketEngine(device_arn, s3_destination_folder, Mock())


def create_program(device: sf.Device):
    gate_args_list = borealis_gbs(device, modes=216, squeezing="high")
    delays = [1, 6, 36]
    n, N = get_mode_indices(delays)
    prog = sf.TDMProgram(N)

    with prog.context(*gate_args_list) as (p, q):
        ops.Sgate(p[0]) | q[n[0]]
        for i in range(len(delays)):
            ops.Rgate(p[2 * i + 1]) | q[n[i]]
            ops.BSgate(p[2 * i + 2], np.pi / 2) | (q[n[i + 1]], q[n[i]])
        ops.MeasureFock() | q[0]

    return prog


def test_targets(braket_engine, paradigm_properties):
    assert braket_engine.target == paradigm_properties["target"]


def test_device(braket_engine, sf_device):
    actual = braket_engine.device
    assert actual.target == sf_device.target
    assert actual.layout == sf_device.layout
    assert actual.compiler == sf_device.compiler
    assert actual.modes == sf_device.modes
    assert actual.layout == sf_device.layout
    assert actual.gate_parameters == sf_device.gate_parameters
    assert actual.certificate == sf_device.certificate


def test_program_not_compiled(braket_engine, shots, s3_destination_folder):
    device = braket_engine.device
    program = create_program(device)
    assert braket_engine.run_async(program, shots=shots, crop=True).target == device.target
    assert braket_engine.aws_device.run.call_count == 1
    bb = sf.io.to_blackbird(program.compile(device=device))
    bb._target["options"] = {"shots": shots}
    braket_engine.aws_device.run.assert_called_with(
        Program(source=bb.serialize()),
        s3_destination_folder=s3_destination_folder,
        shots=shots,
        poll_timeout_seconds=AwsQuantumTask.DEFAULT_RESULTS_POLL_TIMEOUT,
        poll_interval_seconds=AwsQuantumTask.DEFAULT_RESULTS_POLL_INTERVAL,
    )


def test_recompile(braket_engine, shots, s3_destination_folder):
    device = braket_engine.device
    program = create_program(device)
    compiled = program.compile(device=device, shots=shots)
    assert braket_engine.run_async(compiled, recompile=True).target == device.target
    assert braket_engine.aws_device.run.call_count == 1
    braket_engine.aws_device.run.assert_called_with(
        Program(source=sf.io.to_blackbird(compiled.compile(device=device)).serialize()),
        s3_destination_folder=s3_destination_folder,
        shots=shots,
        poll_timeout_seconds=AwsQuantumTask.DEFAULT_RESULTS_POLL_TIMEOUT,
        poll_interval_seconds=AwsQuantumTask.DEFAULT_RESULTS_POLL_INTERVAL,
    )


def test_compiled_same_device(braket_engine, shots, s3_destination_folder):
    device = braket_engine.device
    program = create_program(device)
    compiled = program.compile(device=device, shots=shots)
    assert braket_engine.run_async(compiled).target == device.target
    assert braket_engine.aws_device.run.call_count == 1
    braket_engine.aws_device.run.assert_called_with(
        Program(source=sf.io.to_blackbird(compiled).serialize()),
        s3_destination_folder=s3_destination_folder,
        shots=shots,
        poll_timeout_seconds=AwsQuantumTask.DEFAULT_RESULTS_POLL_TIMEOUT,
        poll_interval_seconds=AwsQuantumTask.DEFAULT_RESULTS_POLL_INTERVAL,
    )


def test_run(braket_engine, shots, result, s3_destination_folder):
    device = braket_engine.device
    program = create_program(device)
    braket_engine.aws_device.run.return_value.result.return_value = result
    assert np.allclose(braket_engine.run(program, shots=shots).samples, result.measurements[0])
    assert braket_engine.aws_device.run.call_count == 1
    bb = sf.io.to_blackbird(program.compile(device=device))
    bb._target["options"] = {"shots": shots}
    braket_engine.aws_device.run.assert_called_with(
        Program(source=bb.serialize()),
        s3_destination_folder=s3_destination_folder,
        shots=shots,
        poll_timeout_seconds=AwsQuantumTask.DEFAULT_RESULTS_POLL_TIMEOUT,
        poll_interval_seconds=AwsQuantumTask.DEFAULT_RESULTS_POLL_INTERVAL,
    )


@pytest.mark.xfail(raises=ValueError)
@patch("braket.strawberryfields_plugin.braket_engine.AwsDevice")
def test_error_blackbird_not_supported(mock_qpu, device_arn, s3_destination_folder):
    capabilities = {
        "braketSchemaHeader": {
            "name": "braket.device_schema.simulators.gate_model_simulator_device_capabilities",
            "version": "1",
        },
        "service": {
            "braketSchemaHeader": {
                "name": "braket.device_schema.device_service_properties",
                "version": "1",
            },
            "executionWindows": [
                {"executionDay": "Everyday", "windowStartHour": "11:00", "windowEndHour": "12:00"}
            ],
            "shotsRange": [1, 10],
            "deviceCost": {"price": 0.25, "unit": "minute"},
            "deviceDocumentation": {
                "imageUrl": "image_url",
                "summary": "Summary on the device",
                "externalDocumentationUrl": "exter doc link",
            },
            "deviceLocation": "us-east-1",
            "updatedAt": "2020-06-16T19:28:02.869136",
        },
        "action": {
            "braket.ir.jaqcd.program": {
                "actionType": "braket.ir.jaqcd.program",
                "version": ["1"],
                "supportedOperations": ["x", "y"],
                "supportedResultTypes": [
                    {
                        "name": "resultType1",
                        "observables": ["observable1"],
                        "minShots": 2,
                        "maxShots": 4,
                    }
                ],
            },
            "braket.ir.openqasm.program": {
                "actionType": "braket.ir.openqasm.program",
                "version": ["1"],
                "supportedOperations": ["x", "y"],
                "supportedResultTypes": [
                    {
                        "name": "resultType1",
                        "observables": ["observable1"],
                        "minShots": 2,
                        "maxShots": 4,
                    },
                ],
                "supportPhysicalQubits": False,
                "supportedPragmas": ["braket_noise_bit_flip", "braket_unitary_matrix"],
                "forbiddenPragmas": [],
                "forbiddenArrayOperations": ["concatenation", "range", "slicing"],
                "requireAllQubitsMeasurement": True,
                "requireContiguousQubitIndices": False,
                "supportsPartialVerbatimBox": True,
                "supportsUnassignedMeasurements": True,
            },
        },
        "paradigm": {
            "braketSchemaHeader": {
                "name": "braket.device_schema.simulators.gate_model_simulator_paradigm_properties",
                "version": "1",
            },
            "qubitCount": 32,
        },
        "deviceParameters": {
            "braketSchemaHeader": {
                "name": "braket.device_schema.simulators.gate_model_simulator_device_parameters",
                "version": "1",
            },
            "paradigmParameters": {},
        },
    }
    mock_qpu.return_value.properties = GateModelSimulatorDeviceCapabilities.parse_obj(capabilities)
    BraketEngine(device_arn, s3_destination_folder, Mock())


@pytest.mark.xfail(raises=ValueError)
def test_error_no_shots(braket_engine):
    program = create_program(braket_engine.device)
    braket_engine.run_async(program)


@pytest.mark.xfail(raises=ValueError)
def test_error_compiled_different_device(braket_engine, shots):
    device = braket_engine.device
    program = create_program(device)
    compiled = program.compile(device=device)
    mock_device = Mock()
    mock_device.target = "foo"
    compiled._compile_info = (mock_device,)
    braket_engine.run_async(compiled, shots=shots)
