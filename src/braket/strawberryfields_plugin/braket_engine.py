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
from braket.device_schema.xanadu import XanaduDeviceCapabilities
from braket.ir.blackbird import Program

from braket.strawberryfields_plugin.braket_job import BraketJob

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
        self._device = sf.Device(spec, cert)
        self._aws_device = aws_device
        self._s3_folder = s3_destination_folder
        self._poll_timeout_seconds = poll_timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds

    @property
    def aws_device(self):
        return self._aws_device

    @property
    def target(self) -> str:
        return self._device.target

    @property
    def device(self) -> sf.Device:
        return self._device

    def run(
        self, program: sf.Program, *, compile_options=None, recompile=False, **kwargs
    ) -> Optional[sf.Result]:
        """Runs a blocking job.

        In the blocking mode, the engine blocks until the job is completed, failed, or
        cancelled. A job in progress can be cancelled with a keyboard interrupt (`ctrl+c`).

        If the job completes successfully, the result is returned; if the job
        fails or is cancelled, ``None`` is returned.

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
        job = self.run_async(
            program, compile_options=compile_options, recompile=recompile, **kwargs
        )
        return sf.Result(job.result)

    def run_async(
        self, program: sf.Program, *, compile_options=None, recompile=False, **kwargs
    ) -> BraketJob:
        """Runs a non-blocking remote job.

        In the non-blocking mode, a ``xcc.Job`` object is returned immediately, and the user can
        manually refresh the status and check for updated results of the job.

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
        run_options = {**program.run_options, **kwargs}
        if "shots" not in run_options:
            raise ValueError("Number of shots must be specified.")
        bb = BraketEngine._compile(program, compile_options, recompile, self._device)
        bb._target["options"] = run_options
        circuit = bb.serialize()
        task = self._aws_device.run(
            Program(source=circuit),
            s3_destination_folder=self._s3_folder,
            shots=run_options["shots"],
            poll_timeout_seconds=self._poll_timeout_seconds,
            poll_interval_seconds=self._poll_interval_seconds,
        )
        return BraketJob(task, self._device)

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