import os
import imp

from paste.script.command import Command
from paste.script.command import BadCommand
from paste.deploy.loadwsgi import appconfig

from django import conf

from multiprocessing import Process

from .utils import redefine_sockets
from .utils import SOCKETS

def utility(stdin, stdout, stderr, settings, argv):
    redefine_sockets(stdin, stdout, stderr)

    # set up django environment
    imp.load_source("settings", settings)
    settings = conf.Settings("settings")
    conf.settings.configure(settings)

    from django.core.management import ManagementUtility
    utility = ManagementUtility(argv)
    utility.execute()

class Manage(Command):
    min_args = 1
    possible_subcommands = 'syncdb',
    summary = 'Manage Django WSGI project'
    usage = 'CONFIG_FILE APP_NAME [%s]' % "|".join(possible_subcommands)
    takes_config_file = 1
    requires_config_file = True

    parser = Command.standard_parser(quiet=True)
    parser.add_option('-n', '--app-name',
                      dest='app_name',
                      metavar='NAME',
                      help="Load the named application (default main)")

    def command(self):
        if not self.args:
            raise BadCommand('You must give a config file')
        if len(self.args) == 2:
            path, command = self.args
            app_name = self.options.app_name
        elif len(self.args) == 3:
            path, app_name, command = self.args
        else:
            raise ValueError("Must provide two or three arguments.")

        app_spec = "config:%s" % path
        base = os.getcwd()

        # load application configuration
        config = appconfig(app_spec, name=app_name, relative_to=base)
        settings = config.get('settings')
        if settings is None:
            raise LookupError("No value given for 'settings'.")
        argv = [self.command_name, command]
        self.process = Process(target=utility,
                               args=SOCKETS + (settings, argv))
        self.process.start()
        self.process.join()
