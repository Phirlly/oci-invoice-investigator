import os

from .configuration import common_settings
from .runtime_configuration import runtime_settings

globals().update(common_settings())
globals().update(runtime_settings(os.environ))
