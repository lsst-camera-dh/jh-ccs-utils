import unittest
import re
from PythonBinding import CcsPythonExecutorThread

# This is the socket text from run 11063 for which the exception handling
# failed (see LSSTTD-1418):
socket_text = b"""
org.lsst.ccs.command.CommandInvocationException: java.io.FileNotFoundException: /gpfs/slac/lsst/fs3/g/data/jobHarness/jh_stage/LCA-11021_RTM/LCA-11021_RTM-012/11063/flat_pair_raft_acq/v0/85812/pd-values_1558834388-for-seq-24-exp-1.txt (No such file or directory)
	at org.lsst.ccs.command.CommandSetBuilder$CommandSetImplementation.invoke(CommandSetBuilder.java:101)
	at org.lsst.ccs.command.CommandSetBuilder$CommandSetImplementation.invoke(CommandSetBuilder.java:77)
	at org.lsst.ccs.command.CompositeCommandSet.invoke(CompositeCommandSet.java:92)
	at org.lsst.ccs.Agent$RunningCommand.lambda$new$1(Agent.java:1052)
	at java.util.concurrent.FutureTask.run(FutureTask.java:266)
	at java.util.concurrent.Executors$RunnableAdapter.call(Executors.java:511)
	at java.util.concurrent.FutureTask.run(FutureTask.java:266)
	at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1142)
	at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:617)
	at java.lang.Thread.run(Thread.java:745)
Caused by: java.io.FileNotFoundException: /gpfs/slac/lsst/fs3/g/data/jobHarness/jh_stage/LCA-11021_RTM/LCA-11021_RTM-012/11063/flat_pair_raft_acq/v0/85812/pd-values_1558834388-for-seq-24-exp-1.txt (No such file or directory)
	at java.io.FileInputStream.open0(Native Method)
	at java.io.FileInputStream.open(FileInputStream.java:195)
	at java.io.FileInputStream.<init>(FileInputStream.java:138)
	at java.io.FileReader.<init>(FileReader.java:72)
	at org.lsst.ccs.subsystem.ts8.FitsUtilities.readPhotoDiodeFile(FitsUtilities.java:54)
	at org.lsst.ccs.subsystem.ts8.FitsUtilities.updatePhotoDiodeValues(FitsUtilities.java:205)
	at org.lsst.ccs.subsystem.ts8.TS8Subsystem.addBinaryTable(TS8Subsystem.java:1133)
	at sun.reflect.GeneratedMethodAccessor75.invoke(Unknown Source)
	at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
	at java.lang.reflect.Method.invoke(Method.java:498)
	at org.lsst.ccs.command.CommandSetBuilder$CommandSetImplementation.invoke(CommandSetBuilder.java:84)
	... 9 more
org.lsst.ccs.command.CommandInvocationException: org.lsst.ccs.command.CommandInvocationException: java.io.FileNotFoundException: /gpfs/slac/lsst/fs3/g/data/jobHarness/jh_stage/LCA-11021_RTM/LCA-11021_RTM-012/11063/flat_pair_raft_acq/v0/85812/pd-values_1558834388-for-seq-24-exp-1.txt (No such file or directory)

	at org.python.core.Py.JavaError(Py.java:552)
	at org.python.core.Py.JavaError(Py.java:543)
	at org.python.core.PyReflectedFunction.__call__(PyReflectedFunction.java:190)
	at org.python.core.PyObject.__call__(PyObject.java:438)
	at org.python.core.PyMethod.instancemethod___call__(PyMethod.java:237)
	at org.python.core.PyMethod.__call__(PyMethod.java:228)
	at org.python.core.PyMethod.__call__(PyMethod.java:223)
	at org.python.core.PyObject._callextra(PyObject.java:620)
	at ccs_scripting_tools$py.sendSynchCommand$4(/gpfs/slac/lsst/fs2/u1/dh/software/centos7-gcc48/prod/0.2.4/jh-ccs-utils-0.1.5/python/ccs_scripting_tools.py:35)
	at ccs_scripting_tools$py.call_function(/gpfs/slac/lsst/fs2/u1/dh/software/centos7-gcc48/prod/0.2.4/jh-ccs-utils-0.1.5/python/ccs_scripting_tools.py)
	at org.python.core.PyTableCode.call(PyTableCode.java:171)
	at org.python.core.PyBaseCode.call(PyBaseCode.java:308)
	at org.python.core.PyBaseCode.call(PyBaseCode.java:199)
	at org.python.core.PyFunction.__call__(PyFunction.java:482)
	at org.python.core.PyMethod.instancemethod___call__(PyMethod.java:237)
	at org.python.core.PyMethod.__call__(PyMethod.java:228)
	at org.python.core.PyMethod.__call__(PyMethod.java:223)
	at org.python.core.PyObject._callextra(PyObject.java:620)
	at ccs_scripting_tools$py.synchCommand$5(/gpfs/slac/lsst/fs2/u1/dh/software/centos7-gcc48/prod/0.2.4/jh-ccs-utils-0.1.5/python/ccs_scripting_tools.py:38)
	at ccs_scripting_tools$py.call_function(/gpfs/slac/lsst/fs2/u1/dh/software/centos7-gcc48/prod/0.2.4/jh-ccs-utils-0.1.5/python/ccs_scripting_tools.py)
	at org.python.core.PyTableCode.call(PyTableCode.java:171)
	at org.python.core.PyBaseCode.call(PyBaseCode.java:308)
	at org.python.core.PyBaseCode.call(PyBaseCode.java:162)
	at org.python.core.PyFunction.__call__(PyFunction.java:434)
	at org.python.core.PyMethod.__call__(PyMethod.java:156)
	at eo_acquisition$py.add_pd_time_history$31(/gpfs/slac/lsst/fs2/u1/dh/software/centos7-gcc48/prod/0.2.4/IandT-jobs-0.2.0/python/eo_acquisition.py:569)
	at eo_acquisition$py.call_function(/gpfs/slac/lsst/fs2/u1/dh/software/centos7-gcc48/prod/0.2.4/IandT-jobs-0.2.0/python/eo_acquisition.py)
	at org.python.core.PyTableCode.call(PyTableCode.java:171)
	at org.python.core.PyBaseCode.call(PyBaseCode.java:171)
	at org.python.core.PyFunction.__call__(PyFunction.java:434)
	at org.python.core.PyMethod.__call__(PyMethod.java:156)
	at eo_acquisition$py.get_readings$32(/gpfs/slac/lsst/fs2/u1/dh/software/centos7-gcc48/prod/0.2.4/IandT-jobs-0.2.0/python/eo_acquisition.py:589)
	at eo_acquisition$py.call_function(/gpfs/slac/lsst/fs2/u1/dh/software/centos7-gcc48/prod/0.2.4/IandT-jobs-0.2.0/python/eo_acquisition.py)
	at org.python.core.PyTableCode.call(PyTableCode.java:171)
	at org.python.core.PyBaseCode.call(PyBaseCode.java:189)
	at org.python.core.PyFunction.__call__(PyFunction.java:446)
	at org.python.core.PyMethod.__call__(PyMethod.java:171)
	at org.python.pycode._pyx11657.run$3(<script>:32)
	at org.python.pycode._pyx11657.call_function(<script>)
	at org.python.core.PyTableCode.call(PyTableCode.java:171)
	at org.python.core.PyBaseCode.call(PyBaseCode.java:139)
	at org.python.core.PyFunction.__call__(PyFunction.java:413)
	at org.python.core.PyMethod.__call__(PyMethod.java:126)
	at org.python.pycode._pyx11657.f$0(<script>:62)
	at org.python.pycode._pyx11657.call_function(<script>)
	at org.python.core.PyTableCode.call(PyTableCode.java:171)
	at org.python.core.PyCode.call(PyCode.java:18)
	at org.python.core.Py.runCode(Py.java:1614)
	at org.python.core.Py.exec(Py.java:1658)
	at org.python.util.PythonInterpreter.exec(PythonInterpreter.java:276)
	at org.lsst.ccs.subsystems.console.jython.JythonInterpreterConsole$JythonProcessingThread.run(JythonInterpreterConsole.java:371)
Caused by: org.lsst.ccs.command.CommandInvocationException: java.io.FileNotFoundException: /gpfs/slac/lsst/fs3/g/data/jobHarness/jh_stage/LCA-11021_RTM/LCA-11021_RTM-012/11063/flat_pair_raft_acq/v0/85812/pd-values_1558834388-for-seq-24-exp-1.txt (No such file or directory)
	at org.lsst.ccs.command.CommandSetBuilder$CommandSetImplementation.invoke(CommandSetBuilder.java:101)
	at org.lsst.ccs.command.CommandSetBuilder$CommandSetImplementation.invoke(CommandSetBuilder.java:77)
	at org.lsst.ccs.command.CompositeCommandSet.invoke(CompositeCommandSet.java:92)
	at org.lsst.ccs.Agent$RunningCommand.lambda$new$1(Agent.java:1052)
	at java.util.concurrent.FutureTask.run(FutureTask.java:266)
	at java.util.concurrent.Executors$RunnableAdapter.call(Executors.java:511)
	at java.util.concurrent.FutureTask.run(FutureTask.java:266)
	at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1142)
	at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:617)
	at java.lang.Thread.run(Thread.java:745)
"""

class FakeSocketConnection:
    def __init__(self, socket_text):
        self.socket_text = socket_text

    def recv(self, arg):
        return self.socket_text

class CcsPythonExecutorThreadTestCase(unittest.TestCase):
    """TestCase subclass for CcsPythonExecutorThread."""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_java_exception_handling(self):
        """Test handling of java exception messages in the socket output."""
        thread_id = b'0'
        my_socket_text = socket_text + b"\ndoneExecution:" + thread_id
        socket_connection = FakeSocketConnection(my_socket_text)
        executor = CcsPythonExecutorThread(thread_id.decode('utf-8'),
                                           socket_connection)
        executor.running = True
        executor.listenToSocketOutput()
        self.assertNotEqual(len(executor.java_exceptions), 0)

if __name__ == '__main__':
    unittest.main()
