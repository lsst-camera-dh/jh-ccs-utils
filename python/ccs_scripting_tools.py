"""
Tools for CCS jython scripts.
"""
try:
    from org.lsst.ccs.scripting import CCS
except ImportError:
    class CcsType(object):
        def attachSubsystem(self, value):
            return NullSubsystem()

    CCS = CcsType()

    class NullSubsystem(object):
        def __init__(self):
            pass
        def synchCommand(self, *args):
            return NullResponse()
        def asynchCommand(self, *args):
            return NullResponse()

    class NullResponse(object):
        def __init__(self):
            pass
        def getResult(self):
            return 1

class SubsystemDecorator(object):
    def __init__(self, ccs_subsystem, logger=None):
        self.ccs_subsystem = ccs_subsystem
        self.logger = logger

    def synchCommand(self, *args):
        if self.logger is not None:
            self.logger.info(args[1])
        return self.ccs_subsystem.synchCommand(*args)

    def asynchCommand(self, *args):
        if self.logger is not None:
            self.logger.info(args[0])
        return self.ccs_subsystem.asynchCommand(*args)

class CcsSubsystems(object):
    def __init__(self, subsystems=None, logger=None):
        if subsystems is None:
            subsystems = dict(ts8='ts8')
        for key, value in subsystems.items():
            self.__dict__[key] = SubsystemDecorator(CCS.attachSubsystem(value),
                                                    logger=logger)
