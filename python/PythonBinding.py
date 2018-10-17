#!/usr/bin/python
import socket
import threading
import time
import random
import re
import sys

class CcsExecutionResult:
    def __init__(self, thread):
        self.thread = thread

    def isRunning(self):
        return self.thread.running

    def getOutput(self):
        while self.thread.running:
            time.sleep(0.1)
        return self.thread.executionOutput


class CcsException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class CcsJythonInterpreter:
    port = 4444
    host = None
    name = None

    def __init__(self, name=None, host=None, port=4444):
        CcsJythonInterpreter.port = port
        if host is None:
            # Get local machine name
            CcsJythonInterpreter.host = socket.gethostname()
        else:
            CcsJythonInterpreter.host = host
        host_and_port = '{}:{}'.format(CcsJythonInterpreter.host,
                                       CcsJythonInterpreter.port)
        try:
            self.socketConnection = CcsJythonInterpreter.__establishSocketConnectionToCcsJythonInterpreter__()
            print('Initialized connection to CCS Python interpreter on host',
                  host_and_port)
        except Exception as eobj:
            print(eobj)
            raise CcsException("Could not establish a connection with " +
                               "CCS Python Interpreter on host " +
                               host_and_port)

        if name is not None:
            name = name.replace("\n", "")
            self.syncExecution("initializeInterpreter " + name)

    @staticmethod
    def __establishSocketConnectionToCcsJythonInterpreter__():
         s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
         s.connect((CcsJythonInterpreter.host, CcsJythonInterpreter.port))
         connectionResult = s.recv(1024).decode('utf-8')
         if "ConnectionRefused" in connectionResult:
            raise CcsException("Connection Refused ")
         return s

    def aSyncExecution(self, statement):
        return self.sendInterpreterServer(statement)

    def syncExecution(self, statement):
        result = self.sendInterpreterServer(statement)
        output = result.getOutput()
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
        with open(fileName, "r") as fd:
            fileContent = fd.read()
        result = self.sendInterpreterServer(fileContent)
        output = result.getOutput()
        return result

    def sendInterpreterServer(self, content):
        threadId = (str(int(round(time.time() * 1000))) + "-" +
                    str(random.randint(0,1000)))
        thread = _CcsPythonExecutorThread(threadId, self.socketConnection)
        thread.executePythonContent(content)
        return CcsExecutionResult(thread)


class _CcsPythonExecutorThread:

    def __init__(self, threadId, s):
        self.s = s
        self.threadId = threadId
        self.outputThread = threading.Thread(target=self.listenToSocketOutput)
        self.java_exceptions = []

    def executePythonContent(self, content):
        self.running = True
        self.outputThread.start()
        content = ("startContent:" + self.threadId + "\n" +
                   content + "\nendContent:" + self.threadId + "\n")
        self.s.send(content.encode('utf-8'))
        return CcsExecutionResult(self)

    def listenToSocketOutput(self):
        re_obj = re.compile(r'.*java.lang.\w*Exception.*')
        self.executionOutput = ""
        while self.running:
            try:
                output = self.s.recv(1024).decode('utf-8')
            except Exception as eobj:
                print(eobj)
                raise CcsException("Communication Problem with Socket")
            for item in output.split('\n'):
                if re_obj.match(item):
                    self.java_exceptions.append(item)
            if "doneExecution:" + self.threadId not in output:
                sys.stdout.write(output)
                sys.stdout.flush()
            else:
                self.running = False
                self.executionOutput \
                    = self.executionOutput.replace("doneExecution:" +
                                                   self.threadId+"\n", "")
        del self.outputThread
