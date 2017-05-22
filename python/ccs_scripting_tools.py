"""
Tools for CCS jython scripts.
"""
from collections import namedtuple, OrderedDict
try:
    from org.lsst.ccs.scripting import CCS
except ImportError:
    # Create non-jython objects and classes to enable testing.
    class CcsType(object):
        "Non-jython proxy for org.lsst.ccs.scripting.CCS"

        def attachSubsystem(self, value):
            """
            Attach a do-nothing object that acts like a CCS subsystem.
            """
            return NullSubsystem()

    CCS = CcsType()

    class NullSubsystem(object):
        """
        A do-nothing class with dummy methods provided by a CCS subsystem.
        """
        def __init__(self):
            pass

        def synchCommand(self, *args):
            "Execute a synchronous CCS command."
            return NullResponse()

        def asynchCommand(self, *args):
            "Execute an asynchronous CCS command."
            return NullResponse()

    class NullResponse(object):
        """
        Do-nothing response class to act as a return object by the
        NullSubsystem methods.
        """
        def __init__(self):
            pass

        def getResult(self):
            "A generic result."
            return 1

class SubsystemDecorator(object):
    """
    Decorator class to overlay logging of the commands sent to a CCS
    subsystem object.
    """
    def __init__(self, ccs_subsystem, logger=None):
        self.ccs_subsystem = ccs_subsystem
        self.logger = logger

    def _log_command(self, args):
        if self.logger is not None:
            command_string = " ".join(["%s" % arg for arg in args])
            self.logger.info(command_string)

    def synchCommand(self, *args):
        "Decorator method for a synchronous command."
        self._log_command(args)
        return self.ccs_subsystem.synchCommand(*args)

    def asynchCommand(self, *args):
        "Decorator method for an asynchronous command."
        self._log_command(args)
        return self.ccs_subsystem.asynchCommand(*args)


CcsVersionInfo = namedTuple('CcsVersionInfo', 'project version rev')

class CcsSubsystems(object):
    """
    Container for collections of CCS subsystems.
    """
    def __init__(self, subsystems, logger=None):
        """
        Constructor.

        Parameters
        ----------
        subsystems : dict
            A dictionary of subsystem names keyed by desired attribute
            name, e.g., dict(ts8='ts8', pd='ts/PhotoDiode',
                             mono='ts/Monochromator')
        logger : logging.Logger, optional
            Logger to be used by the SubsystemDecorator class. Default: None.
        """
        for key, value in subsystems.items():
            self.__dict__[key] = SubsystemDecorator(CCS.attachSubsystem(value),
                                                    logger=logger)
        self._get_version_info(subsystems)

    def _get_version_info(self, subsystems):
        self.subsystems = OrderedDict()
        for subsystem in subsystems:
            result = \
                self.__dict__[subsystem].synchCommand(10, 'getDistributionInfo')
            info = dict()
            for line in result.split('\n'):
                tokens = [x.strip() for x in line.split(':')]
                info[tokens[0]] = tokens[1]
            self.subsystems[subsystem] = CcsVersionInfo(info['Project'],
                                                        info['Project Version'],
                                                        info['Source Code Rev'])
