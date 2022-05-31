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

import pytest
import strawberryfields as sf
from braket.task_result import PhotonicModelTaskResult
from braket.tasks import PhotonicModelQuantumTaskResult
from pydantic import datetime_parse


@pytest.fixture
def device_arn():
    return "arn:aws:braket:us-east-1::device/qpu/xanadu/Borealis"


@pytest.fixture
def shots():
    return 250000


@pytest.fixture
def s3_destination_folder():
    return "test_bucket", "test_folder_prefix"


@pytest.fixture
def service_properties():
    return {
        "executionWindows": [
            {
                "executionDay": "Everyday",
                "windowStartHour": "09:00",
                "windowEndHour": "10:00",
            }
        ],
        "shotsRange": [1, 1000000],
        "deviceCost": {"price": 0.25, "unit": "minute"},
        "deviceDocumentation": {
            "imageUrl": "image_url",
            "summary": "Summary on the device",
            "externalDocumentationUrl": "external doc link",
        },
        "deviceLocation": "us-east-1",
        "updatedAt": "2020-06-16T19:28:02.869136",
    }


@pytest.fixture
def action():
    return {
        "braket.ir.blackbird.program": {
            "actionType": "braket.ir.blackbird.program",
            "version": ["1"],
            "supportedOperations": ["BSGate", "XGate"],
            "supportedResultTypes": [],
        }
    }


@pytest.fixture
def paradigm_properties():
    return {
        "nativeGateSet": ["SGate", "RGate", "BSGate"],
        "modes": {"spatial": 1, "concurrent": 44, "temporal_max": 331},
        "layout": (
            "name template_borealis\n"
            "version 1.0\n"
            "target borealis (shots=1)\n"
            "type tdm (temporal_modes=331, copies=1)\n"
            "\n"
            "float array p0[1, 331] =\n"
            "    {s}\n"
            "float array p1[1, 331] =\n"
            "    {r0}\n"
            "float array p2[1, 331] =\n"
            "    {bs0}\n"
            "float array p3[1, 331] =\n"
            "    {loop0_phase}\n"
            "float array p4[1, 331] =\n"
            "    {r1}\n"
            "float array p5[1, 331] =\n"
            "    {bs1}\n"
            "float array p6[1, 331] =\n"
            "    {loop1_phase}\n"
            "float array p7[1, 331] =\n"
            "    {r2}\n"
            "float array p8[1, 331] =\n"
            "    {bs2}\n"
            "float array p9[1, 331] =\n"
            "    {loop2_phase}\n"
            "\n"
            "Sgate({s}, 0.0) | 43\n"
            "Rgate({r0}) | 43\n"
            "BSgate({bs0}, 1.5707963267948966) | [42, 43]\n"
            "Rgate({loop0_phase}) | 43\n"
            "Rgate({r1}) | 42\n"
            "BSgate({bs1}, 1.5707963267948966) | [36, 42]\n"
            "Rgate({loop1_phase}) | 42\n"
            "Rgate({r2}) | 36\n"
            "BSgate({bs2}, 1.5707963267948966) | [0, 36]\n"
            "Rgate({loop2_phase}) | 36\n"
            "MeasureFock() | 0"
        ),
        "target": "borealis",
        "compiler": ["borealis"],
        "compilerDefault": "borealis",
        "supportedLanguages": ["blackbird:1.0"],
        "gateParameters": {
            "s": [[0.0, 2.0]],
            "r0": [[-1.5707963267948966, 1.5707963267948966]],
            "r1": [[-1.5707963267948966, 1.5707963267948966]],
            "r2": [[-1.5707963267948966, 1.5707963267948966]],
            "bs0": [[0.0, 1.5707963267948966]],
            "bs1": [[0.0, 1.5707963267948966]],
            "bs2": [[0.0, 1.5707963267948966]],
            "loop0_phase": [[-3.141592653589793, 3.141592653589793]],
            "loop1_phase": [[-3.141592653589793, 3.141592653589793]],
            "loop2_phase": [[-3.141592653589793, 3.141592653589793]],
        },
    }


@pytest.fixture
def provider_properties():
    return {
        "loopPhases": [0.673, 0.109, 0.379],
        "schmidtNumber": 1.149,
        "commonEfficiency": 0.472,
        "loopEfficiencies": [0.928, 0.885, 0.85],
        "squeezingParameters": {"low": [0.534], "high": [1.12], "medium": [0.886]},
        "squeezingParametersMean": {
            "low": 0.534,
            "high": 1.12,
            "medium": 0.886,
        },
        "relativeChannelEfficiencies": [
            0.969,
            0.929,
            0.952,
            0.807,
            0.911,
            1.0,
            0.894,
            0.899,
            0.993,
            0.992,
            0.876,
            0.938,
            0.957,
            0.922,
            0.878,
            0.953,
        ],
    }


@pytest.fixture
def sf_device(service_properties, paradigm_properties, provider_properties):
    spec = {k: v for k, v in paradigm_properties.items() if k != "gateParameters"}
    spec["gate_parameters"] = paradigm_properties["gateParameters"]
    finished_at = datetime_parse.parse_datetime(service_properties["updatedAt"])
    cert = {
        "finished_at": f'{finished_at.strftime("%Y-%m-%dT%H:%M:%S.%f")}+00:00',
        "target": paradigm_properties["target"],
        "loop_phases": provider_properties["loopPhases"],
        "schmidt_number": provider_properties["schmidtNumber"],
        "common_efficiency": provider_properties["commonEfficiency"],
        "squeezing_parameters": provider_properties["squeezingParameters"],
        "squeezing_parameters_mean": provider_properties["squeezingParametersMean"],
        "relative_channel_efficiencies": provider_properties["relativeChannelEfficiencies"],
    }
    return sf.Device(spec, cert)


@pytest.fixture
def task_metadata(shots, device_arn):
    return {"taskMetadata": {"id": "task_arn", "shots": shots, "deviceId": device_arn}}


@pytest.fixture
def additional_metadata():
    return {
        "additionalMetadata": {
            "action": {"source": "I'm a Blackbird program"},
            "xanaduMetadata": {"compiledProgram": "I'm a compiled program"},
        }
    }


@pytest.fixture
def result(additional_metadata, task_metadata):
    result = {
        "measurements": [[[0, 1], [2, 3]]],
    }
    result.update(additional_metadata)
    result.update(task_metadata)
    return PhotonicModelQuantumTaskResult.from_object(PhotonicModelTaskResult.parse_obj(result))
