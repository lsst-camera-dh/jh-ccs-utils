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
        """
        Return a list of valid proxy subsytems.
        """
        return self.proxies.keys()

class NullSubsystem(object):
    """
    A do-nothing class with dummy methods to emulate a CCS subsystem.
    """
    def __init__(self):
        pass

    def synchCommand(self, *args):
        "Execute a synchronous CCS command."
        return NullResponse(*args)

    def asynchCommand(self, *args):
        "Execute an asynchronous CCS command."
        return NullResponse(*args)

class Ts8Proxy(NullSubsystem):
    "Fake ts8 subsystem with canned responses to CCS commands."
    def __init__(self):
        super(Ts8Proxy, self).__init__()
        self._fill_responses()

    def _fill_responses(self):
        self.responses = dict()
        self.responses['getREBDeviceNames'] \
            = ProxyResponse(('R00.Reb0', 'R00.Reb1', 'R00.Reb2'))
        self.responses['getREBHwVersions'] \
            = ProxyResponse([808599560, 808599560, 808599560])
        self.responses['getREBSerialNumbers'] \
            = ProxyResponse([305877457, 305892521, 305879138])
        self.responses['printGeometry 3'] = ProxyResponse('''--> R00
---> R00.Reb2
----> R00.Reb2.Sen20
----> R00.Reb2.Sen21
----> R00.Reb2.Sen22
---> R00.Reb1
----> R00.Reb1.Sen10
----> R00.Reb1.Sen11
----> R00.Reb1.Sen12
---> R00.Reb0
----> R00.Reb0.Sen00
----> R00.Reb0.Sen01
----> R00.Reb0.Sen02
''')
    def synchCommand(self, *args):
        command = ' '.join([str(x) for x in args[1:]])
        try:
            return self.responses[command]
        except KeyError:
            return NullResponse()

    def asynchCommand(self, *args):
        command = ' '.join([str(x) for x in args])
        try:
            return self.responses[command]
        except KeyError:
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

class ProxyResponse(NullResponse):
    "Response object with canned response content."
    def __init__(self, content):
        super(ProxyResponse, self).__init__()
        self.content = content

    def getResult(self):
        return self.content

CCS = CcsType()
