"""
Module to enable CCS scripting from Python.
"""
from __future__ import print_function
import sys
import socket
import threading
import logging
import time
import random
import re

logging.basicConfig(format="%(message)s",
                    level=logging.INFO,
                    stream=sys.stdout)
logger = logging.getLogger()


class CcsExecutionResult(object):
    def __init__(self, thread):
        self.thread = thread

    def isRunning(self):
        return self.thread.running

    def getOutput(self):
        while self.thread.running:
            time.sleep(0.1)
        return self.thread.executionOutput


class CcsException(StandardError):
    def __init__(self, *args, **kwds):
        super(CcsException, self).__init__(*args, **kwds)


class CcsJythonInterpreter(object):
    def __init__(self, name=None, host=None, port=4444, verbose=False):
        self.port = port
        if host is None:
            # Get local machine name
            self.host = socket.gethostname()
        else:
            self.host = host
        self.socketConnection = self._establishSocketConnection()
        if verbose:
            print('Initialized connection to CCS Python interpreter on host',
                  self.host, ':', self.port)

        if name is not None:
            name = name.replace("\n", "")
            self.syncExecution("initializeInterpreter " + name)

    def _establishSocketConnection(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host, self.port))
        connectionResult = s.recv(1024)
        if "ConnectionRefused" in connectionResult:
            raise CcsException("Connection Refused")
        return s

    def aSyncExecution(self, statement):
        return self.sendInterpreterServer(statement)

    def syncExecution(self, statement):
        result = self.sendInterpreterServer(statement)
        result.getOutput()
        return result

    def aSyncScriptExecution(self, fileName):
        fo = open(fileName, "r")
        fileContent = fo.read()
        fo.close()
        return self.sendInterpreterServer(fileContent)

    def syncScriptExecution(self, fileName, setup_commands=(), verbose=False):
        if verbose and setup_commands:
            print("Executing setup commands for", fileName)
        for command in setup_commands:
            if verbose:
                print(command)
            self.syncExecution(command)

        if verbose:
            print("Executing %s..." % fileName)
        fo = open(fileName, "r")
        fileContent = fo.read()
        fo.close()
        result = self.sendInterpreterServer(fileContent)
        result.getOutput()
        return result

    def sendInterpreterServer(self, content):
        threadId = str(int(round(time.time() * 1000))) \
                   + "-" + str(random.randint(0, 1000))
        thread = _CcsPythonExecutorThread(threadId, self.socketConnection)
        thread.executePythonContent(content)
        return CcsExecutionResult(thread)


class _CcsPythonExecutorThread(object):

    def __init__(self, threadId, s):
        self.s = s
        self.threadId = threadId
        self.outputThread = threading.Thread(target=self.listenToSocketOutput)
        self.java_exceptions = []

    def executePythonContent(self, content):
        self.running = True
        self.outputThread.start()
        content = "startContent:" + self.threadId + "\n" + content + "\nendContent:" + self.threadId +"\n"
        self.s.send(content)
        return CcsExecutionResult(self)

    def listenToSocketOutput(self):
        re_obj = re.compile(r'.*java.lang.\w*Exception.*')
        self.executionOutput = ""
        while self.running:
            output = self.s.recv(1024)
            for item in output.split('\n'):
                if re_obj.match(item):
                    self.java_exceptions.append(item)
            if "doneExecution:" + self.threadId not in output:
                sys.stdout.write(output)
                sys.stdout.flush()
            self.executionOutput += output
            if "doneExecution:" + self.threadId in output:
                self.running = False
                self.executionOutput = self.executionOutput.replace("doneExecution:"+self.threadId+"\n", "")
        self.outputThread._Thread__stop()


class SubsystemDispatcher(object):
    def __init__(self, interpreter, alias, subsys_name, logger=logger):
        self.interpreter = interpreter
        self.alias = alias
        self.subsys_name = subsys_name
        self.logger = logger
        self.interpreter.syncExecution("%s = CCS.attachSubsystem('%s')" \
                                       % (alias, subsys_name))

    def synchCommand(self, timeout, *args, **kwds):
        try:
            parser = kwds['parser']
        except KeyError:
            parser = self.default_parser

        components = ["%s" % timeout]
        components += ["'%s'" % x if isinstance(x, str) else "%s" % x
                       for x in args]
        jy_args = ', '.join(components)
        self.logger.info(jy_args)
        jython_command = "print %s.synchCommand(%s).getResult()" \
                         % (self.alias, jy_args)
        result = self.interpreter.syncExecution(jython_command)
        return parser(result.getOutput())

    def asynchCommand(self, *args):
        components = ["'%s'" % x if isinstance(x, str) else "%s" % x
                      for x in args]
        jy_args = ', '.join(components)
        self.logger.info(jy_args)
        jython_command = "%s.asynchCommand(%s)" % (self.alias, jy_args)
        self.interpreter.syncExecution(jython_command)

    @staticmethod
    def _cast(token):
        try:
            if token.find('.') != -1 or token.find('e') != -1 \
               or token.find('E') != -1:
                return float(token)
            else:
                return int(token)
        except ValueError:
            if token == 'True':
                return True
            elif token == 'False':
                return False
            return token

    @staticmethod
    def default_parser(ccs_socket_output):
        # Remove trailing whitespace.
        data = ccs_socket_output.rstrip()

        if data.startswith('['):
            # We have a list of items, so cast each item and return the list.
            tokens = data[1:-1].split(', ')
            # Recursively resolve item'd lists.
            result = [SubsystemDispatcher.default_parser(x) for x in tokens]
        else:
            result = SubsystemDispatcher._cast(data)
        return result

class CcsSubsystems(object):
    def __init__(self, subsystems):
        self.interpreter = CcsJythonInterpreter('ccs_interpreter')
        self.interpreter.syncExecution('from org.lsst.ccs.scripting import CCS')
        for key, value in subsystems.items():
            self.__dict__[key] \
                = SubsystemDispatcher(self.interpreter, key, value)
