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
from braket.device_schema.xanadu import XanaduDeviceCapabilities
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


def test_program_not_compiled(braket_engine, shots):
    device = braket_engine.device
    program = create_program(device)
    assert braket_engine.run_async(program, shots=shots).target == device.target
    assert braket_engine.aws_device.run.call_count == 1


def test_recompile(braket_engine, shots):
    device = braket_engine.device
    program = create_program(device)
    compiled = program.compile(device=device, shots=shots)
    assert braket_engine.run_async(compiled, recompile=True).target == device.target
    assert braket_engine.aws_device.run.call_count == 1


def test_compiled_same_device(braket_engine, shots):
    device = braket_engine.device
    program = create_program(device)
    compiled = program.compile(device=device, shots=shots)
    assert braket_engine.run_async(compiled).target == device.target
    assert braket_engine.aws_device.run.call_count == 1


def test_run(braket_engine, shots, result):
    device = braket_engine.device
    program = create_program(device)
    braket_engine.aws_device.run.return_value.result.return_value = result
    assert np.allclose(braket_engine.run(program, shots=shots).samples, result.measurements[0])
    assert braket_engine.aws_device.run.call_count == 1


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
