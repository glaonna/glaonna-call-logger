# Standard Lib
from queue import Queue
import argparse
import logging
import signal
import sys

# Third Party
import sentry_sdk

# Local
from calllogger.plugins import get_plugin
from calllogger import __version__, running, api, settings, telemetry
from calllogger.misc import ThreadExceptionManager
from calllogger.auth import get_token
from calllogger.misc import graceful_exception, terminate

logger = logging.getLogger("calllogger")

# Parse command line args. Only used for version right now.
parser = argparse.ArgumentParser(prog="Quartx CallLogger")
parser.add_argument('--version', action='version', version=f"calllogger {__version__}")
parser.parse_known_args()


def initialise_telemetry(client_info: dict):
    """Collect system metrics and logs."""
    # Enable metrics telemetry
    if settings.collect_metrics and client_info["influxdb_token"]:
        api.InfluxWrite(
            collector=telemetry.collector,
            token=client_info["influxdb_token"],
            default_fields=dict(
                identifier=settings.identifier,
                client=client_info["slug"],
            )
        ).start()

    # Enable logs telemetry
    if settings.collect_logs:
        telemetry.setup_remote_logs(
            client=client_info["slug"],
        )


def main_loop(plugin: str) -> int:
    """Call the selected plugin and wait for program shutdown."""
    running.set()
    tokenauth = get_token()
    queue = Queue(settings.queue_size)
    client_info = api.get_client_info(tokenauth, settings.identifier)

    # Initialise telemetry if we are able to
    initialise_telemetry(client_info)

    # Configure sentry
    plugin = get_plugin(plugin if plugin else client_info["settings"]["plugin"])
    sentry_sdk.set_tag("plugin", plugin.__name__)

    # Start the CDR worker to monitor the record queue
    cdr_thread = api.CDRWorker(queue, tokenauth)
    cdr_thread.start()

    # Start the plugin thread to monitor for call records
    plugin_thread = plugin(_queue=queue)
    plugin_thread.start()

    # Sinse both threads share the same running event
    # If one dies, so should the other.
    cdr_thread.join()
    plugin_thread.join()
    return ThreadExceptionManager.exit_code.value()


# Entrypoint: calllogger
@graceful_exception
def monitor() -> int:
    """Normal logger that calls the users preferred plugin."""
    return main_loop(settings.plugin)


# Entrypoint: calllogger-mock
@graceful_exception
def mockcalls() -> int:
    """Force use of the mock logger."""
    return main_loop("MockCalls")


# Entrypoint: calllogger-getid
@graceful_exception
def getid() -> int:
    identifier = settings.identifier
    print(identifier)
    return 0


# Gracefully shutdown for 'kill <pid>' or docker stop <container>
signal.signal(signal.SIGTERM, terminate)

if __name__ == "__main__":
    # Normally this program will be called from an entrypoint
    # So we will force use of the mock plugin when called directly
    exit_code = mockcalls()
    sys.exit(exit_code)
