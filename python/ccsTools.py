"""
Module to supplement the interface between python and the CCS jython
interpreter.
"""
import os
import shutil
from collections import OrderedDict
from PythonBinding import CcsJythonInterpreter
import siteUtils

_quote = lambda x: "'%s'" % x

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
        self['tsCWD'] = _quote(os.getcwd())
        self['labname'] = _quote(siteUtils.getSiteName())
        self['jobname'] = _quote(siteUtils.getJobName())
        self['CCDID'] = _quote(siteUtils.getUnitId())
        self['UNITID'] = _quote(siteUtils.getUnitId())
        self['LSSTID'] = _quote(siteUtils.getLSSTId())
        try:
            self['RUNNUM'] = _quote(siteUtils.getRunNumber())
        except StandardError:
            self['RUNNUM'] = "no_lcatr_run_number"

        self['ts'] = _quote(os.getenv('CCS_TS', default='ts'))
        self['archon'] = _quote(os.getenv('CCS_ARCHON', default='archon'))

        # The following are only available for certain contexts.
        if os.environ.has_key('CCS_VAC_OUTLET'):
            self['vac_outlet'] = os.getenv('CCS_VAC_OUTLET')
        if os.environ.has_key('CCS_CRYO_OUTLET'):
            self['cryo_outlet'] = os.getenv('CCS_CRYO_OUTLET')
        if os.environ.has_key('CCS_PUMP_OUTLET'):
            self['pump_outlet'] = os.getenv('CCS_PUMP_OUTLET')

        self._read(os.path.join(siteUtils.getJobDir(), configFile))

    def _read(self, configFile):
        if configFile is None:
            return
        configDir = siteUtils.configDir()
        for line in open(configFile):
            key, value = line.strip().split("=")
            self[key.strip()] = _quote(os.path.realpath(os.path.join(configDir, value.strip())))

    def __call__(self):
        """
        Return the setup commands for the CCS script.
        """
        # Set the local variables.
        commands = ['%s = %s' % item for item in self.items()]
        # Append path to the modules used by the jython code.
        commands.append('import sys')
        commands.append('sys.path.append("%s")' % siteUtils.pythonDir())
        return commands


class CcsRaftSetup(CcsSetup):
    """
    Subclass of CcsSetup that will query the eTraveler db tables for
    the sensors in the raft specified as LCATR_UNIT_ID.
    """
    def __init__(self, configFile):
        super(CcsRaftSetup, self).__init__(configFile)
        self._get_ccd_names()
    def _get_ccd_names(self):
        ccdnames = {}
        ccdmanunames = {}
        ccdnames, ccdmanunames = siteUtils.getCCDNames()
#        print "retrieved the following LSST CCD names list"
#        print ccdnames
#        print "retrieved the following Manufacturers CCD names list"
#        print ccdmanunames
        for slot in ccdnames:
#            print "CCD %s is in slot %s" % (ccdnames[slot], slot)
            self['CCD%s' % slot] = _quote(ccdnames[slot])
        for slot in ccdmanunames:
#            print "CCD %s is in slot %s" % (ccdmanunames[slot], slot)
            self['CCDMANU%s' % slot] = _quote(ccdmanunames[slot])
        CCDTYPE = _quote(siteUtils.getUnitType())
#        print "CCDTYPE = %s" % CCDTYPE
        self['sequence_file'] = _quote("NA")
        self['acffile'] = self['itl_acffile']
        self['CCSCCDTYPE'] = _quote("ITL")
        if "RTM" in CCDTYPE.upper() or "ETU" in CCDTYPE.upper():
            if "e2v" in CCDTYPE:
                self['CCSCCDTYPE'] = _quote("E2V")
                self['acffile'] = self['e2v_acffile']
                self['sequence_file'] = self['e2v_seqfile']
            else:
                self['CCSCCDTYPE'] = _quote("ITL")
                self['acffile'] = self['itl_acffile']
                self['sequence_file'] = self['itl_seqfile']
#            print self['sequence_file'], self['tsCWD']
            shutil.copy2(self['sequence_file'].strip("'"),
                         self['tsCWD'].strip("'"))
#            print "The sequence file to be used is %s" % self['sequence_file']
        else:
            if "ITL" in CCDTYPE:
                self['CCSCCDTYPE'] = _quote("ITL")
                self['acffile'] = self['itl_acffile']
            if "e2v" in CCDTYPE:
                self['CCSCCDTYPE'] = _quote("E2V")
                self['acffile'] = self['e2v_acffile']
 #           print "The acffile to be used is %s" % self['acffile']


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
