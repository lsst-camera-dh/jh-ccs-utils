from __future__ import print_function
import os
import shutil
import socket
import datetime
import json
import numpy as np
try:
    import ConfigParser as configparser
except ImportError:
    import configparser
import astropy.io.fits as pyfits
import lsst.eotest.image_utils as imutils
import lsst.eotest.sensor as sensorTest
import lcatr.schema
from lcatr.harness.helpers import dependency_glob
import siteUtils

def make_median_bias_frame(bias_files, sensor_id, acq_job, skip=1):
    """Make a median bias frame from bias files."""
    # Skip the initial frames since the first bias images may have
    # residual signal from not having been cleared properly.
    bias_files = sorted(bias_files)[skip:]
    bias_frame = f'{sensor_id}_{acq_job}_median_bias.fits'
    amp_geom = sensorTest.makeAmplifierGeometry(bias_files[0])
    imutils.superbias_file(bias_files, amp_geom.serial_overscan, bias_frame)
    return bias_frame

def utc_now_isoformat():
    return datetime.datetime.utcnow().isoformat()

def getSensorGains(jobname='fe55_analysis', sensor_id=None):
    if (os.environ.get('LCATR_USE_UNIT_GAINS', 'False') == 'True'
        or os.environ.get("LCATR_SKIP_FE55_ANALYSIS", "False") == "True"):
        return {amp: 1 for amp in range(1, 17)}

    if sensor_id is None:
        sensor_id = siteUtils.getUnitId()
    try:
        gain_file = dependency_glob('%s_eotest_results.fits' % sensor_id,
                                    jobname=jobname)[0]
    except IndexError:
        raise RuntimeError('eotestUtils.getSensorGains: %s %s'
                           % (sensor_id, jobname))
    data = sensorTest.EOTestResults(gain_file)
    amps = data['AMP']
    gains = data['GAIN']
    sensorGains = dict([(amp, gains[amp-1]) for amp in amps])
    return sensorGains

def glob_mask_files(pattern='*_mask.fits'):
    return siteUtils.dependency_glob(pattern, description='Mask files:')

def getTestStandHostName():
    """
    It is assumed that the test stand will be identified by the
    hostname of the dedicated computer used to control it.
    """
    if 'EOTEST_HOST_DEV' in os.environ:
        # For running  in development mode without a real test stand.
        return os.environ['EOTEST_HOST_DEV']
    return socket.gethostname()

def getEotestCalibsFile():
    """
    Return the full path to the eotest calibrations file.
    """
    return os.path.join(siteUtils.configDir(), 'eotest_calibrations.cfg')

def getEotestCalibs():
    """
    Return calibration file names for the current test stand.
    """
    try:
        pars = siteUtils.Parfile(getEotestCalibsFile(), getTestStandHostName())
    except configparser.NoSectionError:
        # Use the "default" section.
        pars = siteUtils.Parfile(getEotestCalibsFile(), 'default')
    return pars

def getSystemNoise(gains):
    """
    Return the system noise for each amplifier channel.  The data are
    read from the local file given in the site-specific eotest
    calibrations file.
    """
    pars = getEotestCalibs()
    if pars['system_noise_file'] is None:
        return None
    data = np.recfromtxt(pars['system_noise_file'], names=('amp', 'noise'))
    sys_noise = {}
    # Multiply by gain to obtain noise in e- rms.
    for amp, noise in zip(data['amp'], data['noise']):
        sys_noise[amp] = gains[amp]*noise
    return sys_noise

def eotest_abspath(path):
    if path is None:
        return None
    return os.path.abspath(path)

def getSystemCrosstalkFile():
    """
    Return the full path to the system crosstalk file as given in the
    site-specific eotest calibrations file.
    """
    pars = getEotestCalibs()
    return eotest_abspath(pars['system_crosstalk_file'])

def getPhotodiodeRatioFile():
    """
    Return the full path to the locally accessible monitoring
    photodiode "ratio" file image as given in the site-specific eotest
    calibrations file.
    """
    pars = getEotestCalibs()
    return eotest_abspath(pars['photodiode_ratio_file'])

def getIlluminationNonUniformityImage():
    """
    Return the full path to the locally accessible illumination
    non-uniformity image as as given in the site-specific eotest
    calibrations file.
    """
    pars = getEotestCalibs()
    return eotest_abspath(pars['illumination_non_uniformity_file'])

def eotestCalibrations():
    """
    Return the lcatr.schema.valid results object for persisting the
    eotest calibration file information.
    """
    pars = getEotestCalibs()
    kwds = dict([(key, str(value)) for key, value in pars.items()])
    kwds['eotest_host'] = getTestStandHostName()
    result = lcatr.schema.valid(lcatr.schema.get('eotest_calibrations'), **kwds)
    return result

def eotestCalibsPersist(*keys, **kwds):
    """
    Loop through specified list of keys in eotest calibration config
    file and persist as lcatr.schema.filerefs.  Return the list of
    filerefs.
    """
    pars = getEotestCalibs()
    results = []
    for key in keys:
        filename = pars[key]
        if filename is not None:
            if not os.path.isfile(filename):
                raise RuntimeError("eotest calibration parameter %s = %s is not a valid file" % (key, filename))
            shutil.copy(filename, '.')
            try:
                md = kwds['metadata'][key]
            except KeyError:
                # Either KeyError signifies that there is no metadata
                # associated with this calibration file.
                md = None
            results.append(lcatr.schema.fileref.make(os.path.basename(filename),
                                                     metadata=md))
    return results

def addHeaderData(fitsfile, **kwds):
    fits_obj = pyfits.open(fitsfile, do_not_scale_image_data=True)
    try:
        hdu = kwds['hdu']
    except KeyError:
        hdu = 0
    for key, value in kwds.items():
        if key == 'clobber':
            continue
        fits_obj[hdu].header[key] = siteUtils.cast(value)
    try:
        clobber = kwds['clobber']
    except KeyError:
        clobber = True
    fits_obj.writeto(fitsfile, overwrite=clobber)

def png_data_product(pngfile, sensor_id):
    """
    This function is provided for backwards compatibility, but it is
    deprecated in favor of the equivalent implementation in siteUtils.
    """
    return siteUtils.png_data_product(pngfile, sensor_id)


class JsonRepackager(object):
    """
    Class to repackage per amp information in the json-formatted
    summary.lims files from each analysis task into the
    EOTestResults-formatted output.

    Attributes
    ----------
    eotest_results : lsst.eotest.sensor.EOTestResults
        Object to contain the EO analysis results.
    """
    _key_map = dict((('gain', 'GAIN'),
                     ('gain_error', 'GAIN_ERROR'),
                     ('psf_sigma', 'PSF_SIGMA'),
                     ('read_noise', 'READ_NOISE'),
                     ('system_noise', 'SYSTEM_NOISE'),
                     ('total_noise', 'TOTAL_NOISE'),
                     ('bright_pixels', 'NUM_BRIGHT_PIXELS'),
                     ('bright_columns', 'NUM_BRIGHT_COLUMNS'),
                     ('dark_pixels', 'NUM_DARK_PIXELS'),
                     ('dark_columns', 'NUM_DARK_COLUMNS'),
                     ('dark_current_95CL', 'DARK_CURRENT_95'),
                     ('dark_current_median', 'DARK_CURRENT_MEDIAN'),
                     ('num_traps', 'NUM_TRAPS'),
                     ('cti_low_serial', 'CTI_LOW_SERIAL'),
                     ('cti_low_serial_error', 'CTI_LOW_SERIAL_ERROR'),
                     ('cti_low_parallel', 'CTI_LOW_PARALLEL'),
                     ('cti_low_parallel_error', 'CTI_LOW_PARALLEL_ERROR'),
                     ('cti_high_serial', 'CTI_HIGH_SERIAL'),
                     ('cti_high_serial_error', 'CTI_HIGH_SERIAL_ERROR'),
                     ('cti_high_parallel', 'CTI_HIGH_PARALLEL'),
                     ('cti_high_parallel_error', 'CTI_HIGH_PARALLEL_ERROR'),
                     ('full_well', 'FULL_WELL'),
                     ('max_frac_dev', 'MAX_FRAC_DEV'),
                     ('row_mean_var_slope', 'ROW_MEAN_VAR_SLOPE'),
                     ('deferred_charge_median', 'DEFERRED_CHARGE_MEDIAN'),
                     ('deferred_charge_stdev', 'DEFERRED_CHARGE_STDEV'),
                     ('ptc_gain', 'PTC_GAIN'),
                     ('ptc_gain_error', 'PTC_GAIN_ERROR'),
                     ('ptc_a00', 'PTC_A00'),
                     ('ptc_a00_error', 'PTC_A00_ERROR'),
                     ('ptc_noise', 'PTC_NOISE'),
                     ('ptc_noise_error', 'PTC_NOISE_ERROR'),
                     ('ptc_turnoff', 'PTC_TURNOFF'),
                     ('bf_xcorr', 'BF_XCORR'),
                     ('bf_xcorr_err', 'BF_XCORR_ERR'),
                     ('bf_ycorr', 'BF_YCORR_ERR'),
                     ('bf_slopex', 'BF_SLOPEX'),
                     ('bf_slopex_err', 'BF_SLOPEX_ERR'),
                     ('bf_slopey', 'BF_SLOPEY'),
                     ('bf_slopey_err', 'BF_SLOPEY_ERR'),
                     ('bf_mean', 'BF_MEAN'),
                     ))
    def __init__(self, outfile='eotest_results.fits', namps=16):
        """
        Constructor

        Parameters
        ----------
        outfile : str, optional
            Output filename of FITS file to contain the results as
            written by self.eotest_results.
        """
        self.has_content = False
        self.eotest_results = sensorTest.EOTestResults(outfile, namps=namps)

    def process_file(self, infile, sensor_id=None, slot=None, raft=None):
        """
        Harvest the EO test results from a summary.lims file.

        Parameters
        ----------
        infile : str
            A JSON-formatted input file, typically a summary.lims file
            produced by the Job Harness.
        """
        with open(infile) as fd:
            summary_info = json.load(fd)
            for result in summary_info:
                no_ccd_selection = ('sensor_id' not in result
                                    and ('slot' not in result
                                         or 'raft' not in result))
                raft_level_match = ('sensor_id' in result
                                    and result['sensor_id'] == sensor_id)
                bot_level_match = ('slot' in result and 'raft' in result
                                   and result['slot'] == slot
                                   and result['raft'] == raft)
                ccd_match = (no_ccd_selection
                             or raft_level_match
                             or bot_level_match)
                if 'amp' in result and ccd_match:
                    self.has_content = True
                    amp = result['amp']
                    for key, value in result.items():
                        if (key.find('schema') == 0 or
                            key not in self._key_map.keys()):
                            continue
                        self.eotest_results.add_seg_result(amp,
                                                           self._key_map[key],
                                                           value)

    def write(self, outfile=None, clobber=True):
        """
        Write the collected results to a FITS file.

        Parameters
        ----------
        outfile : str, optional
            Output filename, if None (default), then use the filename
            set in the constructor.
        clobber : bool, optional
            Flag whether to overwrite an existing file with the same name.
            Default: True
        """
        if not self.has_content:
            return
        self.eotest_results.write(outfile=outfile, clobber=clobber)

    def process_files(self, summary_files, sensor_id=None, slot=None,
                      raft=None):
        """
        Process a list of summary.lims files.

        Parameters
        ----------
        summary_files : list
            A list of summary.lims files.
        """
        for item in summary_files:
            self.process_file(item, sensor_id=sensor_id, slot=slot, raft=raft)
