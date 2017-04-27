"""
Module to supplement the interface between python and the CCS jython
interpreter.
"""
import os
import shutil
from collections import OrderedDict
from PythonBinding import CcsJythonInterpreter
import siteUtils
import camera_components

class CcsSetup(OrderedDict):
    """
    The context-specific setup commands for executing a CCS script
    written in jython.  These commands set variables and paths that
    are known in the calling python code and which are needed by the
    jython script.
    """
    def __init__(self, configFile):
        """
        configFile contains the names of the site-specific
        configuration files.  File basenames are provided in
        configFile, and the full paths are constructed in the
        _read(...) method.
        """
        super(CcsSetup, self).__init__()
        self.commands = []
        self['tsCWD'] = os.getcwd()
        self['labname'] = siteUtils.getSiteName()
        self['jobname'] = siteUtils.getJobName()
        self['CCDID'] = siteUtils.getUnitId()
        self['UNITID'] = siteUtils.getUnitId()
        self['LSSTID'] = siteUtils.getLSSTId()
        try:
            self['RUNNUM'] = siteUtils.getRunNumber()
        except StandardError:
            self['RUNNUM'] = "no_lcatr_run_number"

        self['ts'] = os.getenv('CCS_TS', default='ts')
        self['archon'] = os.getenv('CCS_ARCHON', default='archon')

        # The following are only available for certain contexts.
        if os.environ.has_key('CCS_VAC_OUTLET'):
            self['vac_outlet'] = os.getenv('CCS_VAC_OUTLET')
        if os.environ.has_key('CCS_CRYO_OUTLET'):
            self['cryo_outlet'] = os.getenv('CCS_CRYO_OUTLET')
        if os.environ.has_key('CCS_PUMP_OUTLET'):
            self['pump_outlet'] = os.getenv('CCS_PUMP_OUTLET')

        self._read(os.path.join(siteUtils.getJobDir(), configFile))

    def __setitem__(self, key, value):
        super(CcsSetup, self).__setitem__(key, "'%s'" % str(value))

    def set_item(self, key, value):
        super(CcsSetup, self).__setitem__(key, value)

    def _read(self, configFile):
        if configFile is None:
            return
        configDir = siteUtils.configDir()
        for line in open(configFile):
            key, value = line.strip().split("=")
            self[key.strip()] = os.path.realpath(os.path.join(configDir, value.strip()))

    def __call__(self):
        """
        Return the setup commands for the CCS script.
        """
        # Insert path to the modules used by the jython code.
        self.commands.insert(0, 'sys.path.append("%s")' % siteUtils.pythonDir())
        self.commands.insert(0, 'import sys')
        # Set the local variables.
        self.commands.extend(['%s = %s' % item for item in self.items()])
        return self.commands


class CcsRaftSetup(CcsSetup):
    """
    Subclass of CcsSetup that will query the eTraveler db tables for
    the sensors in the raft specified as LCATR_UNIT_ID.
    """
    def __init__(self, configFile):
        super(CcsRaftSetup, self).__init__(configFile)
        self.commands.append('from collections import namedtuple')
        self.commands.append("SensorInfo = namedtuple('SensorInfo', 'sensor_id manufacturer_sn'.split())")
        self.commands.append("ccd_names = dict()")
        self._get_ccd_names()
    def _get_ccd_names(self):
        raft_id = siteUtils.getUnitId()
        raft = camera_components.Raft.create_from_etrav(raft_id)
        for slot in raft.slot_names:
            sensor = raft.sensor(slot)
            self.set_item('ccd_names["%s"]' % slot, 'SensorInfo("%s", "%s")'
                          % (str(sensor.sensor_id),
                             str(sensor.manufacturer_sn)))
        ccd_type = str(raft.sensor_type.split('-')[0])
        self['ccd_type'] = ccd_type
        if ccd_type == 'ITL':
            self.set_item('sequence_file', self['itl_seqfile'])
        elif ccd_type == 'E2V':
            self.set_item('sequence_file', self['e2v_seqfile'])
        else:
            raise RuntimeError('Invalid ccd_type: %s' % ccd_type)
        shutil.copy2(self['sequence_file'].strip("'"),
                     self['tsCWD'].strip("'"))


def ccsProducer(jobName, ccsScript, ccs_setup_class=None, verbose=True):
    """
    Run the CCS data acquistion script under the CCS jython interpreter.
    """
    if ccs_setup_class is None:
        ccs_setup_class = CcsSetup

    ccs = CcsJythonInterpreter("ts")
    configDir = siteUtils.configDir()
    setup = ccs_setup_class('%s/acq.cfg' % configDir)

    result = ccs.syncScriptExecution(siteUtils.jobDirPath(ccsScript), setup(),
                                     verbose=verbose)
    output = open("%s.log" % jobName, "w")
    output.write(result.getOutput())
    output.close()
    if result.thread.java_exceptions:
        raise RuntimeError("java.lang.Exceptions raised:\n%s"
                           % '\n'.join(result.thread.java_exceptions))
