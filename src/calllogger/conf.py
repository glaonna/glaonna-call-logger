# Standard lib
from functools import cached_property
from pathlib import PosixPath
import logging
import base64
import sys
import os

# Third Party
from decouple import config, undefined, UndefinedValueError
import appdirs

__all__ = ["settings", "merge_settings"]
logger = logging.getLogger(__name__)


def decode_env(env, default="") -> str:
    """Decode a Base64 encoded environment variable."""
    encode_check = "ZW5jb2RlZDo="
    value = os.environ.get(env, default)
    if value and value.startswith(encode_check):
        value = value[len(encode_check):]
        value = base64.b64decode(value).decode("utf8")
    return value


def merge_settings(ins, prefix="", **defaults):
    """
    Populate class defined settings from environment variables.

    This function will scan for class variables that have type annotations
    and check if there is a environment variable with the same name.
    It will then asigned the environment variable value to that class variable.

    If a class variable exists with type annotation and has no default value and
    there is no environment variable with the variable name. Then the program
    will quit and complain of missing environment variables.

    :param ins: The class instance where the variables will be set.
    :param prefix: Only check environment variables with the given prefix. Defaults to "".
    :param defaults: Extra keyword only arguments to override defaults.
    """
    # Merge class variable defaults with override defaults
    ins.__dict__.update(defaults)
    errors = []

    # Check if all settings with annotations have a environment variable set for them
    for key, cast in ins.__class__.__dict__.get("__annotations__", {}).items():
        fallback = ins.__class__.__dict__.get(key, undefined)
        default = defaults.get(key, fallback)
        env_key = f"{prefix}{key}".upper()

        try:
            ins.__dict__[key] = config(env_key, default, cast)
        except UndefinedValueError:
            errors.append(f"Missing required environment variable: {env_key}")
        except (ValueError, TypeError):
            errors.append(f"Invalid type for setting '{env_key}', expecting '{cast.__name__}'")

    # Report any error to user and quit
    if errors:
        for msg in errors:
            print(msg)
        sys.exit(0)


class Settings:
    """
    Settings class that allows settings
    to be overridden by environment variables.
    """

    #: Timeout in seconds to sleep between errors.
    timeout: int = 3
    #: Multiplier that increases the timeout on continuous errors.
    timeout_decay: float = 1.5
    #: The max the timeout can be after continuous decay.
    max_timeout: int = 300
    #: Size of the call queue
    queue_size: int = 1_000
    # The domain to send the call logs to, used in development.
    domain: str = "https://quartx.ie"
    #: Set to true to enable debug logging.
    debug: bool = False

    # Environment name, e.g. 'testing', 'production'
    environment: str = "Testing"
    # Flag to indicate if program is dockerized
    dockerized: bool = False
    # Device registration cutoff timeout in seconds
    device_reg_timeout: int = 3 * 60 * 60
    # Device registration check timeout in seconds
    device_reg_check: int = 60

    def __init__(self):
        merge_settings(self)

    @property
    def sentry_dsn(self) -> str:
        return decode_env("SENTRY_DSN")

    @property
    def reg_key(self) -> str:
        return decode_env("REG_KEY")

    @cached_property
    def datastore(self) -> PosixPath:
        """The location for the datastore."""
        if locale := os.environ.get("DATA_LOCATION"):
            locale = PosixPath(locale).resolve()
        else:
            # Use appdirs to select datastore location if locale is not given
            locale = appdirs.user_data_dir("quartx-calllogger")
            locale = PosixPath(locale)

        logger.debug("Datastore Location: %s", locale)
        os.makedirs(locale, exist_ok=True)
        return locale

    @property
    def plugin(self):
        """The name of the plugin to use."""
        if "PLUGIN" in os.environ["PLUGIN"]:
            return os.environ["PLUGIN"]
        else:
            print("Missing required environment variable: PLUGIN")
            sys.exit(0)


settings = Settings()
