#!/usr/bin/env python

import signal
import sys
from functools import partial

import beer_garden
import beer_garden.api.http
import beer_garden.api.thrift
from beer_garden import progressive_backoff
from beer_garden.app import Application
from beer_garden.bg_utils.mongo import setup_database
from beer_garden.config import generate_logging, generate, migrate


def signal_handler(signal_number, stack_frame):
    beer_garden.logger.info("Last call! Looks like we gotta shut down.")
    beer_garden.application.stop()

    beer_garden.logger.info(
        "Closing time! You don't have to go home, but you can't stay here."
    )
    if beer_garden.application.is_alive():
        beer_garden.application.join()

    beer_garden.logger.info(
        "Looks like the Application is shut down. Have a good night!"
    )


def generate_logging_config():
    generate_logging(sys.argv[1:])


def generate_config():
    generate(sys.argv[1:])


def migrate_config():
    migrate(sys.argv[1:])


def main():
    # Absolute first thing to do is load the config
    beer_garden.load_config(sys.argv[1:])

    # Need to create the application before registering the signal handlers
    beer_garden.application = Application()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Todo - these checks should really move into the application
    # Ensure we have a mongo connection
    progressive_backoff(
        partial(setup_database, beer_garden.config),
        beer_garden.application,
        "Unable to connect to mongo, is it started?",
    )

    # Ensure we have message queue connections
    progressive_backoff(
        beer_garden.application.clients["pika"].is_alive,
        beer_garden.application,
        "Unable to connect to rabbitmq, is it started?",
    )
    progressive_backoff(
        beer_garden.application.clients["pyrabbit"].is_alive,
        beer_garden.application,
        "Unable to connect to rabbitmq admin interface. "
        "Is the management plugin enabled?",
    )

    # We could already be shutting down, in which case we don't want to start
    if not beer_garden.application.stopped():
        beer_garden.logger.info("Hi, what can I get you to drink?")
        beer_garden.application.start()

        beer_garden.logger.info("All set! Let me know if you need anything else!")

        # Need to be careful here because a simple join() or wait() can cause the main
        # python thread to lock out our signal handler, which means we cannot shut down
        # gracefully in some circumstances. So instead we use pause() to wait on a
        # signal. If you choose to change this please test thoroughly when deployed via
        # system packages (apt/yum) as well as python packages and docker.
        # Thanks! :)
        signal.pause()

    beer_garden.logger.info("Don't forget to drive safe!")


if __name__ == "__main__":
    main()
