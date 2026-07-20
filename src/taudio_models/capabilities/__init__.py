# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Built-in public capabilities (import for registration side effects)."""

from taudio_models.capabilities import denoise_speech as _denoise_speech  # noqa: F401
from taudio_models.capabilities import separate_demucs as _separate_demucs  # noqa: F401
from taudio_models.capabilities import separate_hpss as _separate_hpss  # noqa: F401
from taudio_models.capabilities import separate_karaoke as _separate_karaoke  # noqa: F401
from taudio_models.capabilities import separate_vocal as _separate_vocal  # noqa: F401
