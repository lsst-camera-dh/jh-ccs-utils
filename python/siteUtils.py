"""
Site-specific utilities for harnessed jobs.
"""
import os
import sys
import re
import glob
import shutil
import pickle
import fnmatch
import warnings
import subprocess
import pandas as pd
from collections import OrderedDict, defaultdict
import json
try:
    import ConfigParser as configparser
except ImportError:
    import configparser
import matplotlib.pyplot as plt
import lcatr.schema
import lcatr.harness.helpers
from eTraveler.clientAPI.connection import Connection
from camera_components import camera_info


def getCCDNames():
    topdir = os.getcwd()
    topparts = topdir.split('/')
    activity_id = topparts[len(topparts)-1]
    if not topdir:
        raise RuntimeError('cannot determine top-level data directory')
    limsurl = os.getenv('LCATR_LIMS_URL', default='')
    if '/Prod' in limsurl:
        print("Connecting to eTraveler Prod")
        conn = Connection('homer', 'Prod', prodServer=False)
    else:
        print("Connecting to eTraveler Dev")
        conn = Connection('homer', 'Dev', prodServer=False)
    if not conn:
        raise RuntimeError('unable to authenticate')

    ccdnames = {}
    ccdmanunames = {}
    rsp = []
    try:
        rsp = conn.getHardwareHierarchy(experimentSN=getUnitId(),
                                        htype=getUnitType(),
                                        noBatched='false')
        print("Results from getHardwareHierarchy unfiltered:")
        iDict = 0
        for d in rsp:
#            print('Examining array element %d' % (iDict))
            isaccd = False
            ccd_sn = ""
            ccd_slot = ""
            ccd_htype = ""
            ccd_manu_sn = ""
            got_ccd_manu = False
            for k in d:
#                print('For key {0} value is {1}'.format(k, d[k]))
                if ('child_hardwareTypeName' in str(k) and
                    ('itl-ccd' in str(d[k].lower()) or
                     'e2v-ccd' in str(d[k].lower()))):
                    isaccd = True
                    print("found CCD specs")
                if isaccd and 'child_experimentSN' in str(k):
                    ccd_sn = str(d[k])
                    print("CCD SN = %s" % ccd_sn)
                if isaccd and 'slotName' in str(k):
                    ccd_slot = str(d[k])
                    print("slot = %s" % ccd_slot)
                if isaccd and 'child_hardwareTypeName' in str(k):
                    ccd_htype = str(d[k])
                if (isaccd and ccd_sn != "" and ccd_htype != "" and
                    not got_ccd_manu):
                    print("trying to get Manufacturer ID for ccd_sn=%s , ccd_htype=%s" % (ccd_sn, ccd_htype))
                    try:
                        ccd_manu_sn = conn.getManufacturerId(experimentSN=ccd_sn,
                                                             htype=ccd_htype)
                        print('Manufacturer ID: ', ccd_manu_sn)
                        got_ccd_manu = True
                    except ValueError as eobj:
                        print('Operation failed with ValueError:', eobj)
                    except Exception as eobj:
                        print('Operation failed with exception:', eobj)
                        sys.exit(1)
            iDict += 1
            if isaccd:
                ccdnames[ccd_slot] = ccd_sn
                ccdmanunames[ccd_slot] = ccd_manu_sn
    except Exception as eobj:
        print('Operation failed with exception: ')
        print(str(eobj))
        sys.exit(1)

    print("Returning the following list of CCD names and locations")
    print("ccdnames")
    return ccdnames, ccdmanunames


def get_lcatr_envs():
    """
    Extract the LCATR_* environment variables for updating the runtime
    environment of the harnessed job code to be executed in
    parsl_wrapper.
    """
    lcatr_envs = dict()
    for key, value in os.environ.items():
        if key.startswith('LCATR'):
            lcatr_envs[key] = value
    return lcatr_envs


class ETResults(dict):
    """
    dict subclass to retrieve and provided access to harnessed job
    results from the eT database for a specified run.

    The keys are the schema names and each dict value is a pandas
    dataframe containing the results with a column for each schema
    entry.
    """
    amp_names = 'C10 C11 C12 C13 C14 C15 C16 C17 C07 C06 C05 C04 C03 C02 C01 C00'.split()
    wf_amp_names = 'C00 C01 C02 C03 C04 C05 C06 C07'.split()
    def __init__(self, run, user='ccs', prodServer=True):
        """
        Parameters
        ----------
        run: str
            Run number.  If it ends in 'D', the Dev database will be
            queried.
        user: str ['ccs']
            User id to pass to the etravelerAPI.connection.Connnection
            initializer.
        prodServer: bool [True]
            Flag to use the prod or dev eT server.
        """
        super(ETResults, self).__init__()
        db_name = 'Dev' if run.endswith('D') else 'Prod'
        conn = Connection(user, db_name, prodServer=prodServer)
        self.results = conn.getRunResults(run=run)
        self._extract_schema_values()

    def _extract_schema_values(self):
        steps = self.results['steps']
        for jobname, schema_data in steps.items():
            for schema_name, entries in schema_data.items():
                schema_data = defaultdict(list)
                for entry in entries[1:]:
                    for colname, value in entry.items():
                        schema_data[colname].append(value)
                self[schema_name] = pd.DataFrame(data=schema_data)

    def get_amp_data(self, schema_name, field_name):
        df = self[schema_name]
        amp_data = defaultdict(dict)
        for i in range(len(df)):
            row = df.iloc[i]
            det_name = '_'.join((row.raft, row.slot))
            if 'SW' in det_name:
                amp_data[det_name][self.wf_amp_names[row.amp-1]] \
                    = row[field_name]
            else:
                amp_data[det_name][self.amp_names[row.amp-1]] = row[field_name]
        return amp_data

    def get_amp_gains(self, det_name, schema_name='fe55_BOT_analysis'):
        gain_field = {'fe55_BOT_analysis': 'gain',
                      'ptc_BOT': 'ptc_gain'}
        amp_data = self.get_amp_data(schema_name, gain_field[schema_name])
        return {i+1: amp_data[det_name][amp_name] for i, amp_name
                in enumerate(amp_data[det_name])}


def extract_amp_data(summary_lims_file, schema_name, field_name,
                     camera=None):
    """
    Extract the per-amp results from the summary.lims file for the
    desired schema and field.
    """
    if camera is None:
        camera = camera_info.camera_object
    with open(summary_lims_file) as fd:
        et_data = json.load(fd)
    amp_data = defaultdict(dict)
    for item in et_data:
        if item['schema_name'] != schema_name:
            continue
        det_name = '_'.join((item['raft'], item['slot']))
        channels = {amp: segment.getName() for amp, segment
                    in enumerate(camera.get(det_name), 1)}
        if len(channels) == 8:
            # obs_lsst in lsst_distrib v20.0.0 has the order
            # of channels reversed in its WF sensor detector object,
            # so invert it here.
            channels = dict(zip(range(8, 0, -1), channels.values()))
        amp = item['amp']
        amp_data[det_name][channels[amp]] = item[field_name]
    return amp_data


def get_analysis_run(target_analysis_type, bot_eo_config_file=None):
    """
    Get the run number to use for retrieving outputs from a previous
    run as specific in the 'ANALYSIS_RUNS' section of the BOT EO
    config file.  If no run was specified, return None.
    """
    cp = configparser.ConfigParser(allow_no_value=True,
                                   inline_comment_prefixes=('#',))
    cp.optionxform = str
    bot_eo_config_file = get_bot_eo_config_file(bot_eo_config_file)
    if bot_eo_config_file is None:
        return None
    cp.read(bot_eo_config_file)
    if 'ANALYSIS_RUNS' not in cp:
        return None
    for analysis_type, run in cp.items('ANALYSIS_RUNS'):
        if analysis_type.lower() == target_analysis_type.lower():
            return run
    return None


def get_bot_eo_config_file(bot_eo_config_file=None):
    """
    Retrieve the bot_eo_acq_cfg filename from the acq.cfg file.
    """
    if bot_eo_config_file is not None:
        return bot_eo_config_file
    acq_cfg = os.path.join(os.environ['LCATR_CONFIG_DIR'], 'acq.cfg')
    with open(acq_cfg, 'r') as fd:
        for line in fd:
            if line.startswith('bot_eo_acq_cfg'):
                return line.strip().split('=')[1].strip()
    return None


class HarnessedJobFilePaths:
    """
    Class to provide original physical filepaths to files generated by
    harnessed jobs.
    """
    def __init__(self, user='ccs', prodServer=False):
        """
        Parameters
        ----------
        user: str
            Operator's userid.
        prodServer: bool [False]
            Flag to use the prod eT server.  If False, then use the dev
            eT server.
        """
        self.user = user
        self.prodServer = prodServer
        self.resp = dict()
        try:
            self._get_acq_run()
        except:
            # The run number is not set by in lcatr.cfg nor in the
            # bot_eo_config_file, so by setting to None, the
            # `dependency_glob` function will use the current run
            # number.
            self.acq_run = None
        self.query_file_paths(self.acq_run)

    def _get_acq_run(self):
        """Get the acquisition run if specified."""
        if 'LCATR_ACQ_RUN' in os.environ:
            self.acq_run = os.environ['LCATR_ACQ_RUN']
            return
        cp = configparser.ConfigParser(allow_no_value=True,
                                       inline_comment_prefixes=('#', ))
        cp.optionxform = str    # allow for case-sensitive keys
        cp.read(get_bot_eo_config_file())
        acq_config = dict(_ for _ in cp.items('ACQUIRE'))
        self.acq_run = acq_config.get('ACQ_RUN', None)
        os.environ['LCATR_ACQ_RUN'] = self.acq_run

    def query_file_paths(self, run):
        """
        Parameters
        ----------
        run: str
            Run number that was assigned by eT.
        """
        if run is None:
            return
        db_name = 'Dev' if run.endswith('D') else 'Prod'
        conn = Connection(self.user, db_name, prodServer=self.prodServer)
        self.resp[run] = conn.getRunFilepaths(run=str(run))

    def get_files(self, jobname, glob_pattern, run=None):
        """
        Get files for a harnessed job using the specified glob pattern.
        """
        if run is None:
            run = self.acq_run
        print('HarnessedJobFilePaths.get_files:', jobname, glob_pattern)
        pattern = glob_pattern.replace('?', '.').replace('*', '.*')
        re_obj = re.compile(pattern)
        files = []
        for item in self.resp[run][jobname]:
            if re_obj.findall(item['originalPath']):
                files.append(item['originalPath'])
        return sorted(files)


def cast(value):
    if value == 'None':
        return None
    try:
        if value.find('.') == -1 and value.find('e') == -1:
            return int(value)
        else:
            return float(value)
    except ValueError:
        # Cannot cast as either int or float so just return the
        # value as-is (presumably a string).
        return value

def getUnitId():
    return os.environ['LCATR_UNIT_ID']

def getLSSTId():
    return os.environ['LCATR_UNIT_ID']

def getUnitType():
    return os.environ['LCATR_UNIT_TYPE']

def getRunNumber():
    return os.environ['LCATR_RUN_NUMBER']

def getCcdVendor():
    default = 'ITL'
    unit_id = getUnitType()
    unit_parts = unit_id.split('-')[0]
    if len(unit_parts) > 0:
        vendor = unit_id.split('-')[0]
        if vendor not in ('ITL', 'E2V', 'e2v'):
            if 'rsa' not in unit_id.lower():
                raise RuntimeError("Unrecognized CCD vendor for unit id %s"
                                   % unit_id)
            else:
                vendor = default
    elif 'rsa' not in unit_id.lower():
        raise RuntimeError("Unrecognized CCD vendor for unit id %s" % unit_id)
    else:
        vendor = default

    return vendor

def getJobName():
    """
    The name of the harnessed job.
    """
    return os.environ['LCATR_JOB']

def getProcessName(jobName=None):
    if jobName is None:
        myJobName = getJobName()
    else:
        myJobName = jobName

    if 'LCATR_PROCESS_NAME_PREFIX' in os.environ:
        myJobName = '_'.join((os.environ['LCATR_PROCESS_NAME_PREFIX'],
                              myJobName))
    if 'LCATR_PROCESS_NAME_SUFFIX' in os.environ:
        myJobName = '_'.join((myJobName,
                              os.environ['LCATR_PROCESS_NAME_SUFFIX']))

    if (os.environ.get('LCATR_RECOVERED_ACQ_DATA', False) == 'True' and
        myJobName.endswith('_acq')):
        myJobName += '_recovery'

    return myJobName

def getJobDir(jobName=None):
    """
    Full path of the harnessed job scripts.
    """
    if jobName is None:
        jobName = getJobName()
    return os.path.join(os.environ['LCATR_INSTALL_AREA'], jobName,
                        os.environ['LCATR_VERSION'])

def jobDirPath(fileName, jobName=None):
    """
    Prepend the job directory to the script filename, thereby giving
    the full path to that script.
    """
    return os.path.join(getJobDir(jobName), fileName)

def getSiteName():
    """
    Return the site or laboratory name
    """
    return os.environ['SITENAME']

def pythonDir():
    """
    Return directory containing the python scripts for this package.
    """
    return os.path.join(os.environ['JHCCSUTILSDIR'], 'python')

def configDir():
    """
    Return the full path to the directory containing the site-specific
    configuration files.
    """
    hj_config = \
        os.path.join(os.environ['HARNESSEDJOBSDIR'], 'config', getSiteName())
    return os.environ.get('LCATR_CONFIG_DIR', hj_config)

def datacatalog_query(query, folder=None, site=None):
    from DataCatalog import DataCatalog
    if folder is None:
        folder = os.environ['LCATR_DATACATALOG_FOLDER']
    if site is None:
        site = getSiteName()
    datacat = DataCatalog(folder=folder, site=site)
    return datacat.find_datasets(query)

def print_file_list(description, file_list, use_basename=False):
    if description is not None:
        print(description)
    for item in file_list:
        if use_basename:
            print("  ", os.path.basename(item))
        else:
            print("  ", item)
    sys.stdout.flush()

def extractJobId(datacat_path):
    """Extract the eTraveler job ID from the filename path."""
    return int(os.path.basename(os.path.split(datacat_path)[0]))

def datacatalog_glob(pattern, testtype=None, imgtype=None, description=None,
                     sort=False, job_id=None):
    sensor_id = getUnitId()
    if testtype is None or imgtype is None:
        raise RuntimeError("Both testtype and imgtype values must be provided.")
    query = ' && '.join(('LSST_NUM=="%(sensor_id)s"',
                         'TESTTYPE=="%(testtype)s"',
                         'IMGTYPE=="%(imgtype)s"')) % locals()
    datasets = datacatalog_query(query)
    file_lists = {}
    for item in datasets.full_paths():
        if fnmatch.fnmatch(os.path.basename(item), pattern):
            my_job_id = extractJobId(item)
            if my_job_id not in file_lists:
                file_lists[my_job_id] = []
            file_lists[my_job_id].append(item)
    if job_id is None:
        job_id = max(file_lists.keys())
    file_list = file_lists[job_id]
    if sort:
        file_list = sorted(file_list)
    print_file_list(description, file_list)
    return file_list


def dependency_glob(pattern, jobname=None, paths=None, description=None,
                    sort=False, user='ccs', acq_jobname=None):
    infile = 'hj_fp_server.pkl'
    if os.path.isfile(infile):
        with open(infile, 'rb') as fd:
            HJ_FILEPATH_SERVER = pickle.load(fd)
    else:
        HJ_FILEPATH_SERVER = HarnessedJobFilePaths()

    if acq_jobname is None and jobname is not None and '_acq' in jobname:
        acq_jobname = jobname

    analysis_runs = dict(pixel_defects_BOT=get_analysis_run('badpixel'),
                         bias_frame_BOT=get_analysis_run('bias'),
                         flat_pairs_BOT=get_analysis_run('linearity'),
                         nonlinearity_BOT=get_analysis_run('nonlinearity'))

    if acq_jobname is not None and HJ_FILEPATH_SERVER.acq_run is not None:
        file_list = HJ_FILEPATH_SERVER.get_files(acq_jobname, pattern)
    elif jobname in analysis_runs and analysis_runs[jobname] is not None:
        file_list = HJ_FILEPATH_SERVER.get_files(jobname, pattern,
                                                 run=analysis_runs[jobname])
    else:
        file_list = lcatr.harness.helpers.dependency_glob(pattern,
                                                          jobname=jobname,
                                                          paths=paths)
    if sort:
        file_list = sorted(file_list)
    print_file_list(description, file_list)
    return file_list

def packageVersions(versions_filename='installed_versions.txt'):
    versions_file = os.path.join(os.environ['INST_DIR'], versions_filename)
    if not os.path.isfile(versions_file):
        return []
    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read(versions_file)
    results = []
    schema = lcatr.schema.get('package_versions')
    for section in parser.sections():
        for package, version in parser.items(section):
            results.append(lcatr.schema.valid(schema, package=package,
                                              version=version))
    return results

def parse_package_versions_summary(summary_lims_file):
    package_versions = OrderedDict()
    summary = json.loads(open(summary_lims_file).read())
    for result in summary:
        if result['schema_name'] == 'package_versions':
            package_versions[result['package']] = result['version']
    if len(package_versions) == 0:
        return None
    return package_versions

def persist_ccs_versions(results, version_file='ccs_versions.txt'):
    if not os.path.isfile(version_file):
        raise RuntimeError("persist_ccs_versions: version file not found.")
    schema = lcatr.schema.get('package_versions')
    with open(version_file) as fp:
        for line in fp:
            tokens = [x.strip() for x in line.strip().split('=')]
            results.append(lcatr.schema.valid(schema, package=tokens[0],
                                              version=tokens[1]))
    return results

def persist_reb_info(results, reb_info_file='reb_info.txt'):
    if not os.path.isfile(reb_info_file):
        raise RuntimeError("persist_reb_info: REB info file not found.")
    schema = lcatr.schema.get('REBVersionsBefore')
    with open(reb_info_file) as fp:
        kwds = dict()
        for i, line in enumerate(fp):
            reb_name, firmware, sn = line.strip().split()
            kwds['REB%iname' % i] = reb_name
            kwds['REB%ifirmware' % i] = firmware
            kwds['REB%iSN' % i] = sn
        results.append(lcatr.schema.valid(schema, **kwds))
    return results


def get_git_commit_info(repo_path, check_status=True):
    '''
    Get the git hash for current HEAD of the requested repo path.

    Parameters
    ----------
    repo_path: str
        Path to the git repository.
    check_status: bool [True]
        If True, then run `git status` to check if the working tree
        has uncommitted changes.

    Returns
    -------
    (str, str):  Tuple of the git hash and tag.  If the current HEAD
        does not correspond to a tag, return the tag as None.
    '''
    if check_status:
        print(repo_path)
        command = f'cd {repo_path}; git status'
        print(subprocess.check_output(command, shell=True).decode('utf-8'))
        sys.stdout.flush()

    command = f'cd {repo_path}; git rev-parse HEAD'
    git_hash = subprocess.check_output(command, shell=True)\
                         .decode('utf-8').strip()

    command = f'cd {repo_path}; git show-ref --tags | tail -1'
    latest_tag = subprocess.check_output(command, shell=True)\
                           .decode('utf-8').strip()

    tag = latest_tag.split('/')[-1] if latest_tag.startswith(git_hash) \
          else None

    return git_hash, tag


def jobInfo():
    results = packageVersions()
    results.append(lcatr.schema.valid(lcatr.schema.get('job_info'),
                                      job_name=os.environ['LCATR_JOB'],
                                      job_id=os.environ['LCATR_JOB_ID']))
    acq_run = os.environ.get('LCATR_ACQ_RUN', getRunNumber())
    skip_fe55_analysis = os.environ.get('LCATR_SKIP_FE55_ANAYLSIS', 'False')
    use_unit_gains = os.environ.get('LCATR_USE_UNIT_GAINS', skip_fe55_analysis)
    results.append(lcatr.schema.valid(lcatr.schema.get('run_info'),
                                      acq_run=acq_run,
                                      use_unit_gains=use_unit_gains))

    # Get fp-scripts repo info
    git_hash, git_tag = None, None
    repo_path = os.environ.get('LCATR_FP_SCRIPTS_REPO_DIR', None)
    if repo_path is not None:
        try:
            git_hash, git_tag = get_git_commit_info(repo_path)
        except Exception as eobj:
            print('Error encountered retrieving fp-scripts git info:\n', eobj)

    results.append(lcatr.schema.valid(lcatr.schema.get('fp-scripts_info'),
                                      git_hash=str(git_hash),
                                      git_tag=str(git_tag)))

    return results

class Parfile(dict):
    def __init__(self, infile, section):
        super(Parfile, self).__init__()
        parser = configparser.ConfigParser()
        parser.read(infile)
        for key, value in parser.items(section):
            self[key] = cast(value)

class DataCatalogMetadata(dict):
    """
    Class to handle metadata passed to the eTraveler for registering
    files with metadata in the Data Catalog.
    """
    def __init__(self, **kwds):
        super(DataCatalogMetadata, self).__init__(**kwds)
    def __call__(self, **kwds):
        my_dict = dict()
        my_dict.update(self)
        my_dict.update(kwds)
        return my_dict

def get_prerequisite_job_id(pattern, jobname=None, paths=None,
                            sort=False):
    """
    Extract the job id of the prerequisite harnesssed job from the
    associated data files (using the dependency_glob pattern),
    assuming that it is included in the folder name.  The Job Harness
    and eTraveler tools do not have a way of providing this
    information, even though the eTraveler db tables do contain it, so
    we are forced to use this ad hoc method.
    """
    files = dependency_glob(pattern, jobname=jobname, paths=paths, sort=sort)
    #
    # The job id is supposed to be the name of the lowest-level folder
    # containing the requested files.
    #
    print(files[0])
    job_id = os.path.split(os.path.split(files[0])[0])[1]
    return job_id

def get_datacatalog_glob_job_id(pattern, testtype=None, imgtype=None,
                                sort=False):
    """
    Extract the job id of the harnessed job that produced the
    requested data files assuming that it is included in the folder
    name.  Ideally, this information would be in the metadata for
    these files, but it is not so we are forced to use this ad hoc
    method.
    """
    files = datacatalog_glob(pattern, testtype=testtype, imgtype=imgtype,
                             sort=sort)
    #
    # The job id is supposed to be the name of the lowest-level folder
    # containing the requested files.
    #
    job_id = os.path.split(os.path.split(files[0])[0])[1]
    return job_id

def aggregate_job_ids():
    """
    Use lcatr.harness.helpers.dependency_jobids to collect the job ids
    for the harnessed jobs on which the current job depends.  If
    previous dependencies have produced pickle files containing their
    dependency job ids, aggregate them into a common dictionary and
    persist them in a pickle file which downstream jobs can access.
    """
    pickle_file = 'dependency_job_ids.pkl'
    my_dependencies = lcatr.harness.helpers.dependency_jobids()
    prior_job_id_files = lcatr.harness.helpers.dependency_glob(pickle_file)
    if prior_job_id_files:
        for item in prior_job_id_files:
            job_ids = pickle.load(open(item, 'r'))
            if job_ids:
                my_dependencies.update(job_ids)
    pickle.dump(my_dependencies, open(pickle_file, 'w'))
    return my_dependencies

def make_fileref(current_path, folder=None, metadata=None,
                 datatype='LSSTSENSORTEST'):
    if folder is not None:
        filename = os.path.basename(current_path)
        if not os.path.isdir(folder):
            os.mkdir(folder)
        new_path = os.path.join(folder, filename)
        shutil.copy(current_path, new_path)
        current_path = new_path
    return lcatr.schema.fileref.make(current_path, datatype=datatype,
                                     metadata=metadata)

def make_png_file(callback, png_file, *args, **kwds):
    try:
        result = callback(*args, **kwds)
        plt.savefig(png_file)
        return result
    except Exception as eobj:
        print("Exception raised while creating %s:" % png_file)
        print(str(eobj))
    finally:
        plt.clf()

def png_data_product(pngfile, lsst_num):
    file_prefix = lsst_num
    try:
        my_prefix = '_'.join((lsst_num, getRunNumber()))
        if pngfile.startswith(my_prefix):
            file_prefix = my_prefix
    except KeyError as eobj:
        # Run number not available.
        pass
    return pngfile[len(file_prefix)+1:-len('.png')]

def persist_png_files(file_pattern, lsst_id, png_files=None,
                      folder=None, metadata=None):
    if metadata is None:
        metadata = dict()
    md = DataCatalogMetadata(**metadata)
    if png_files is None:
        png_files = glob.glob(file_pattern)
    png_filerefs = []
    for png_file in png_files:
        dp = png_data_product(png_file, lsst_id)
        png_filerefs.append(make_fileref(png_file, folder=folder,
                                         metadata=md(DATA_PRODUCT=dp,
                                                     LsstId=lsst_id)))
    return png_filerefs


def get_job_acq_configs(base_config=None):
    """
    Get the config file entries for the desired acquistion from the
    base config file entry.

    Parameters
    ----------
    base_config: str [None]
        File path to the base config file containing the names of all
        the config parameters for the run.  If None, then defaults to
        ${LCATR_CONFIG_DIR}/acq.cfg.

    Returns
    -------
    dict: dictionary of config parameters.  Both keys and values are
        returned as strings, so that clients are responsible for casting
        values appropriately.

    Notes
    -----
    For backwards-compatibility, this code parses each key-value pair
    rather than using configparser, which has syntax requirements that
    are not satisfied by existing files.
    """
    if base_config is None:
        base_config = os.path.join(os.environ['LCATR_CONFIG_DIR'], 'acq.cfg')

    config_dict = dict()
    with open(base_config, 'r') as fd:
        for line in fd:
            if line.startswith('#') or '=' not in line:
                continue
            tokens = line.strip().split('=')
            config_dict[tokens[0].strip()] = tokens[1].strip()
    return config_dict
