"""
Do-nothing python versions of CCS jython objects and classes to
enable testing.
"""
class CcsType(object):
    "Python proxy for the org.lsst.ccs.scripting.CCS jython object."

    def attachSubsystem(self, value):
        """
        Attach a do-nothing object that has the CCS subsystem interface.
        """
        return NullSubsystem()

    def setThrowExceptions(self, value):
        "Do-nothing function."
        pass

class NullSubsystem(object):
    """
    A do-nothing class with dummy methods to emulate a CCS subsystem.
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
        return '123'

CCS = CcsType()
