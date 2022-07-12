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

from typing import Optional

import strawberryfields as sf
from blackbird import BlackbirdProgram
from braket.aws import AwsDevice, AwsQuantumTask, AwsSession
from braket.device_schema import DeviceActionType
from braket.device_schema.xanadu import XanaduDeviceCapabilities
from braket.ir.blackbird import Program
from strawberryfields import TDMProgram

from braket.strawberryfields_plugin.braket_job import BraketJob

from ._version import __version__

_SF_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


class BraketEngine:
    """
    A class for using Amazon Braket as a Strawberry Fields Engine

    Args:
        device_arn (str): AWS quantum device arn.
        s3_destination_folder (AwsSession.S3DestinationFolder): NamedTuple with bucket (index 0)
            and key (index 1) that is the results destination folder in S3.
        aws_session (Optional[AwsSession]): An AwsSession object created to manage
            interactions with AWS services, to be supplied if extra control
            is desired. Default: None
        poll_timeout_seconds (float): Total time in seconds to wait for
            results before timing out.
        poll_interval_seconds (float): The polling interval for results in seconds.

    Examples:
        >>> from braket.strawberryfields_plugin import BraketEngine
        >>> eng = BraketEngine("device_arn_1")
    """

    def __init__(
        self,
        device_arn: str,
        s3_destination_folder: Optional[AwsSession.S3DestinationFolder] = None,
        aws_session: Optional[AwsSession] = None,
        poll_timeout_seconds: float = AwsQuantumTask.DEFAULT_RESULTS_POLL_TIMEOUT,
        poll_interval_seconds: float = AwsQuantumTask.DEFAULT_RESULTS_POLL_INTERVAL,
    ) -> None:
        aws_device = AwsDevice(device_arn, aws_session=aws_session)
        user_agent = f"BraketStrawberryfieldsPlugin/{__version__}"
        aws_device.aws_session.add_braket_user_agent(user_agent)
        capabilities: XanaduDeviceCapabilities = aws_device.properties
        if DeviceActionType.BLACKBIRD not in capabilities.action:
            raise ValueError(f"Device {aws_device.name} does not support photonic circuits")

        self._aws_device = aws_device
        self._target = capabilities.paradigm.target
        self._s3_folder = s3_destination_folder
        self._poll_timeout_seconds = poll_timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds

    @property
    def aws_device(self) -> AwsDevice:
        """AwsDevice: The underlying AwsDevice that makes calls to the Amazon Braket service."""
        return self._aws_device

    @property
    def target(self) -> str:
        """str: The name of the target device used by the engine."""
        return self._target

    @property
    def device(self) -> sf.Device:
        """sf.Device: The representation of the target device.

        This gets the latest calibration data from the Braket service.
        """
        self._aws_device.refresh_metadata()
        return BraketEngine._new_device(self._aws_device)

    def run(
        self, program: sf.Program, *, compile_options=None, recompile=False, **kwargs
    ) -> Optional[sf.Result]:
        """Runs a quantum task to completion and returns its result.

        This is a blocking call that waits until the Braket quantum task is complete.

        If the job completes successfully, the result is returned;
        if the job fails or is cancelled, ``None`` is returned.

        Args:
            program (strawberryfields.Program): the quantum circuit
            compile_options (None, Dict[str, Any]): keyword arguments for :meth:`.Program.compile`
            recompile (bool): Specifies if ``program`` should be recompiled
                using ``compile_options``, or if not provided, the default compilation options.

        Keyword Args:
            shots (int, optional): The number of shots for which to run the job. If this
                argument is not provided, the shots are derived from the given ``program``.

        Returns:
            Optional[sf.Result]: The job result if successful, and ``None`` otherwise
        """
        result = self.run_async(
            program, compile_options=compile_options, recompile=recompile, **kwargs
        ).result
        if not result:
            return None
        output = result.get("output")
        # crop vacuum modes arriving at the detector before the first computational mode
        if output and isinstance(program, TDMProgram) and kwargs.get("crop", False):
            output[0] = output[0][:, :, program.get_crop_value() :]
        return sf.Result(result)

    def run_async(
        self, program: sf.Program, *, compile_options=None, recompile=False, **kwargs
    ) -> BraketJob:
        """Creates a Braket quantum task and returns a ``BraketJob` wrapping the task.

        The user can check the status of the job or retrieve results,
        the latter of which is a blocking call.

        Args:
            program (strawberryfields.Program): the quantum circuit
            compile_options (None, Dict[str, Any]): keyword arguments for :meth:`.Program.compile`
            recompile (bool): Specifies if ``program`` should be recompiled
                using ``compile_options``, or if not provided, the default compilation options.

        Keyword Args:
            shots (Optional[int]): The number of shots for which to run the job. If this
                argument is not provided, the shots are derived from the given ``program``.

        Returns:
            BraketJob: The created Braket job
        """
        # Update the run options if provided
        temp_run_options = {**program.run_options, **kwargs}
        skip_run_keys = ["crop"]
        run_options = {
            key: temp_run_options[key] for key in temp_run_options.keys() - skip_run_keys
        }
        if "shots" not in run_options:
            raise ValueError("Number of shots must be specified.")
        device = self.device
        bb = BraketEngine._compile(program, compile_options, recompile, device)
        bb._target["options"] = run_options
        circuit = bb.serialize()
        task = self._aws_device.run(
            Program(source=circuit),
            s3_destination_folder=self._s3_folder,
            shots=run_options["shots"],
            poll_timeout_seconds=self._poll_timeout_seconds,
            poll_interval_seconds=self._poll_interval_seconds,
        )
        return BraketJob(task, device)

    @staticmethod
    def _new_device(aws_device: AwsDevice) -> sf.Device:
        capabilities: XanaduDeviceCapabilities = aws_device.properties
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
        finished_at = f"{capabilities.service.updatedAt.strftime(_SF_DATETIME_FORMAT)}+00:00"
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
        return sf.Device(spec, cert)

    @staticmethod
    def _compile(
        program: sf.Program, compile_options, recompile, device: sf.Device
    ) -> BlackbirdProgram:
        compile_options = compile_options or {}

        if recompile or program.compile_info is None:
            return sf.io.to_blackbird(program.compile(device=device, **compile_options))

        if not program.compile_info or (
            program.compile_info[0].target == device.target
            and program.compile_info[0]._spec == device._spec
        ):
            # Program is already compiled for this device
            return sf.io.to_blackbird(program)

        # Program already compiled for different device but recompilation disallowed by the user
        program_device = program.compile_info[0]
        compiler_name = compile_options.get("compiler", device.default_compiler)
        raise ValueError(
            f"Cannot use program compiled with {program_device.target} for target {device.target}. "
            f'Pass the "recompile=True" keyword argument to compile with {compiler_name}.'
        )
