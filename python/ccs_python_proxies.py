"""
Do-nothing python versions of CCS jython objects and classes to
enable testing.
"""
class CcsType(object):
    "Python proxy for the org.lsst.ccs.scripting.CCS jython object."
    def __init__(self):
        self.proxies = {'ts8-proxy': Ts8Proxy(),
                        'subsystem-proxy': NullSubsystem()}

    def attachSubsystem(self, value):
        """
        Attach a proxy subsystem object that has the CCS subsystem interface.
        """
        return self.proxies[value]

    def setThrowExceptions(self, value):
        "Do-nothing function."
        pass

    @property
    def subsystem_names(self):
        return self.proxies.keys()

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

class Ts8Proxy(NullSubsystem):
    def __init__(self):
        super(Ts8Proxy, self).__init__()
        self._fill_responses()

    def _fill_responses(self):
        self.responses = dict()
        self.responses['getREBDeviceNames'] \
            = ProxyResponse(('R00.Reb0', 'R00.Reb1', 'R00.Reb2'))
        self.responses['getREBHwVersions'] = ProxyResponse((1, 2, 3))
        self.responses['getREBSerialNumbers'] = ProxyResponse((4, 5, 6))

    def synchCommand(self, *args):
        command = ' '.join([str(x) for x in args[1:]])
        return self.responses[command]

    def asynchCommand(self, *args):
        command = ' '.join([str(x) for x in args])
        return self.responses[command]

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

class ProxyResponse(NullResponse):
    def __init__(self, content):
        super(ProxyResponse, self).__init__()
        self.content = content

    def getResult(self):
        return self.content

CCS = CcsType()
