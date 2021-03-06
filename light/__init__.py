import argparse
import falcon
import multiprocessing

import gunicorn.app.base

from gunicorn.six import iteritems

from .framework import route_framework, load_driver
from . import backend


def number_of_workers():
    """Determine the number of workers to spin up."""
    return (multiprocessing.cpu_count() * 2) + 1


class StandaloneApplication(gunicorn.app.base.BaseApplication):
    """Our standalone application that we will launch."""

    def __init__(self, app, options=None):
        """Take options from main(). app should be a Falcon app."""
        self.options = options or {}
        self.application = app
        super(StandaloneApplication, self).__init__()

    def load_config(self):
        """Load the provided configuration if one was provided."""
        config = dict([(key, value) for key, value in iteritems(self.options)
                       if key in self.cfg.settings and value is not None])
        for key, value in iteritems(config):
            self.cfg.set(key.lower(), value)

    def load(self):
        """Load our application."""
        return self.application


def main():
    """This is the function which is installed as 'illuminate'."""

    parser = argparse.ArgumentParser(description='Start the Light app.')
    parser.add_argument(
        '-H', '--host', type=str, dest="host", default="localhost",
        help='Host or IP to bind to.'
    )
    parser.add_argument(
        '-P', '--port', type=str, dest='port', default="8080",
        help='Port to bind to.'
    )
    parser.add_argument(
        '-W', '--num-workers', type=int, dest='workers',
        default=number_of_workers(),
        help='Number of workers to boot (default: CPU_COUNT * 2 + 1)'
    )
    parser.add_argument(
        '-D', '--driver', type=str, dest='driver',
        default='disk:demo_db',
        help='Driver with store name, such as disk:<folder name> or mysql:<database name>'
    )

    args = parser.parse_args()

    dbdriver, dbstore = args.driver.split(':', 1)[0:2]
    options = {
        'bind': '%s:%s' % (args.host, args.port),
        'workers': args.workers,
        'dbdriver': dbdriver,
        'dbstore': dbstore,
    }

    # Instantiate the backend driver (TODO: Make this generic and a configurable)
    backend.current_driver = load_driver(options)

    if not backend.current_driver:
        print('Cannot find driver {d}\n'.format(d=options['dbdriver']))
        return 1

    # Create a Falcon app.
    app = falcon.API()

    # Add our routes for our framework.
    route_framework(app)

    # Launch our app.
    StandaloneApplication(app, options).run()
