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

import os

import boto3
import pytest
import strawberryfields as sf
from braket.aws import AwsDevice
from braket.aws.aws_session import AwsSession

from braket.strawberryfields_plugin import BraketEngine

BOREALIS_ARN = "arn:aws:braket:us-east-1::device/qpu/xanadu/Borealis"


@pytest.fixture(scope="session")
def boto_session():
    profile_name = os.environ["AWS_PROFILE"]
    return boto3.session.Session(profile_name=profile_name)


@pytest.fixture(scope="session")
def aws_session(boto_session):
    return AwsSession(boto_session)


def test_engine_creation(aws_session):
    engine = BraketEngine(BOREALIS_ARN, aws_session=aws_session)
    aws_device = AwsDevice(BOREALIS_ARN, aws_session=aws_session)
    assert engine.aws_device == aws_device
    actual_device = engine.device
    capabilities = aws_device.properties
    paradigm = capabilities.paradigm
    target = paradigm.target
    spec = {
        "target": target,
        "layout": paradigm.layout,
        "modes": {k: int(v) for k, v in paradigm.modes.items()},
        "compiler": paradigm.compiler,
        "gate_parameters": paradigm.gateParameters,
    }
    provider = capabilities.provider
    finished_at = f"{capabilities.service.updatedAt.strftime('%Y-%m-%dT%H:%M:%S.%f')}+00:00"
    cert = {
        "finished_at": finished_at,
        "target": target,
        "loop_phases": provider.loopPhases,
        "schmidt_number": provider.schmidtNumber,
        "common_efficiency": provider.commonEfficiency,
        "loop_efficiencies": provider.loopEfficiencies,
        "squeezing_parameters_mean": provider.squeezingParametersMean,
        "relative_channel_efficiencies": provider.relativeChannelEfficiencies,
    }
    expected_device = sf.Device(spec, cert)
    assert actual_device.target == expected_device.target
    assert actual_device.layout == expected_device.layout
    assert actual_device.compiler == expected_device.compiler
    assert actual_device.modes == expected_device.modes
    assert actual_device.layout == expected_device.layout
    assert actual_device.gate_parameters == expected_device.gate_parameters
    assert actual_device.certificate == expected_device.certificate
