"""
Module to make mosaics of raw CCD FITS files in the LSST focal
plane using the tools in lsst.afw.cameraGeom and the focal plane
layout in obs_lsst.
"""
import sys
import matplotlib.pyplot as plt
import pandas as pd
import lsst.afw.cameraGeom.utils as cgu
from lsst.afw.display.rgb import ZScaleMapping, displayRGB
import lsst.daf.persistence as dp


__all__ = ['make_fp_mosaic', 'display_image', 'get_frame_info']


def raw_callback(*args, verbose=True, **kwds):
    """Wrapper of cgu.rawCallback to enable progress to be written
    to the screen with a dot for each CCD."""
    if verbose:
        sys.stdout.write('.')
        sys.stdout.flush()
    return cgu.rawCallback(*args, **kwds)


def make_fp_mosaic(repo, expId, det_names=None, outfile=None, bin_size=10,
                   verbose=False):
    """
    Function to make a mosaic of raw image data in the LSST focal plane.

    Parameters
    ----------
    repo: str
        Path to the data repo containing the raw images.
    expId: int
        The expId to use.
    det_names: list-like [None]
        List of detectors to render, e.g., ['R22_S11', 'R22_S12', ...].
        If None, the all detectors in the focal plane will be plotted.
    outfile: str [None]
        Name of FITS file to write with the mosaicked data.  If None,
        then no file will be written.
    bin_size: int [10]
        Rebinning size in pixels.
    verbose: bool [False]
        Flag to print dots indicating progress of CCD processing.

    Returns
    -------
    lsst.afw.ImageF:  Image containing the mosaic.
    """
    butler = dp.Butler(repo)
    camera = butler.get('camera')
    callback = lambda *args, **kwds: raw_callback(*args, verbose=verbose,
                                                  **kwds)
    image_source = cgu.ButlerImage(butler, 'raw', expId=expId,
                                   callback=callback, verbose=verbose)
    image = cgu.showCamera(camera, imageSource=image_source,
                           binSize=bin_size, detectorNameList=det_names)
    if outfile is not None:
        image.writeFits(outfile)

    return image


def display_image(image, contrast=1, figsize=(8, 8)):
    """Use matplotlib to plot an afw.image.Image."""
    plt.figure(figsize=figsize)
    scaled_image = ZScaleMapping(image, contrast=contrast)\
        .makeRgbImage(image, image, image)
    displayRGB(scaled_image)
    plt.axis('off')


def get_frame_info(butler, run):
    """Extract the per CCD metadata for a given run."""
    data = defaultdict(list)
    datarefs = butler.subset('raw', run=run)
    for dataref in datarefs:
        md = dataref.get('raw_md')
        data['test_type'].append(md.getScalar('TESTTYPE'))
        data['image_type'].append(md.getScalar('IMGTYPE'))
        data['exp_id'].append(dataref.dataId['expId'])
        data['exptime'].append(md.getScalar('EXPTIME'))
        data['run'].append(run)
    return pd.DataFrame(data=data)
