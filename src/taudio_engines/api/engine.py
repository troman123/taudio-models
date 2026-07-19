from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from taudio_engines.api.types import ModelInfo, ModelParams, RunResult


class Engine(ABC):
    """Fixed engine interface — every model implements the same surface."""

    @abstractmethod
    def info(self) -> ModelInfo:
        raise NotImplementedError

    @abstractmethod
    def run(
        self,
        input_path: Path,
        output_dir: Path,
        params: Optional[ModelParams] = None,
    ) -> RunResult:
        """
        Run inference.

        Implementations must:
        - validate params via ModelParams.validated(self.info())
        - ensure required weights via cache.ensure_model when needed
        - write stem files under output_dir
        - return RunResult with Artifact paths
        """
        raise NotImplementedError
