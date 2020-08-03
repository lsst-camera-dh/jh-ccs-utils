"""
Module to make mosaics of raw CCD FITS files in the LSST focal
plane using the tools in lsst.afw.cameraGeom and the focal plane
layout in obs_lsst.
"""
import copy
import numpy as np
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath
from lsst.afw.cameraGeom import utils as cgu
import lsst.daf.persistence as dp


__all__ = ['RawImageSource', 'make_fp_mosaic']


class RawImageSource:
    """
    ImageSource class to pass to the cameraGeom.makeImageFromCamera
    function to make focal plane mosaics.
    """
    ix = np.concatenate((np.arange(8), np.arange(7, -1, -1)))
    iy = np.concatenate((np.zeros(8, dtype=int), np.ones(8, dtype=int)))
    e2V_rafts = ['R30', 'R31', 'R32', 'R33', 'R34',
                        'R21', 'R22', 'R23', 'R24',
                        'R11', 'R12', 'R13', 'R14']
    def __init__(self, butler, visit):
        """
        Parameters
        ----------
        butler: lsst.daf.Persistence.Butler
            Data butler pointing to the repo containing the raw image data.
        visit: int
            Visit or exposure id number for the desired dataset.
        """
        self.butler = butler
        self.visit = visit
        self.isTrimmed = True
        self.background = 0

    def getCcdImage(self, detector, imageFactory, binSize=1):
        """
        Mosaic the amplifier data from a raw file into a composed
        CCD with the prescan and overscan regions removed.

        Parameters
        ----------
        detector: lsst.afw.cameraGeom.Detector
            The Detector object for the desired CCD.
        imageFactory: lsst.afw.Image
            Image class to use to make a Image object to pass to
            the cameraGeom mosaicking code.
        binSize: int [1]
            Rebinning size in pixels.

        Returns
        -------
        (lsst.afw.Image, )
        """
        image = imageFactory(detector.getBBox())
        datarefs = self.butler.subset('raw_amp', visit=self.visit,
                                      detector=detector.getId())
        for dataref, amp_info in zip(datarefs, detector):
            hdu = dataref.dataId['channel']
            raft = dataref.dataId['raftName']
            raw_bbox = amp_info.getRawDataBBox()
            dx = raw_bbox.getWidth()
            dy = raw_bbox.getHeight()
            full_segment = dataref.get('raw_amp').getImage()
            bias = full_segment[amp_info.getRawHorizontalOverscanBBox()]
            full_segment -= afwMath.makeStatistics(bias,
                                                   afwMath.MEANCLIP).getValue()
            imaging_segment = imageFactory(full_segment, raw_bbox)
            xoffset = self.ix[hdu-1]*dx
            yoffset = self.iy[hdu-1]*dy
            data = copy.deepcopy(imaging_segment.array)
            #if amp_info.getRawFlipX():  # This only works if the yaml files
                                         # describing the camera are correct.
            if (raft not in self.e2V_rafts) or hdu < 9:
                data = data[:, ::-1]
            if amp_info.getRawFlipY():
                data = data[::-1, :]
            image.array[yoffset: yoffset + dy, xoffset: xoffset + dx] += data
        my_image = imageFactory(image.array[::-1, :])
        if binSize > 1:
            my_image = afwMath.binImage(my_image, binSize)
        return (my_image, )


def make_fp_mosaic(repo, visit, det_names=None, outfile=None, bin_size=10):
    """
    Function to make a mosaic of raw image data in the LSST focal plane.

    Parameters
    ----------
    repo: str
        Path to the data repo containing the raw images.
    visit: int
        The visit or expId to use.
    det_names: list-like [None]
        List of detectors to render, e.g., ['R22_S11', 'R22_S12', ...].
        If None, the all detectors in the focal plane will be plotted.
    outfile: str [None]
        Name of FITS file to write with the mosaicked data.  If None,
        then no file will be written.
    bin_size: int [10]
        Rebinning size in pixels.

    Returns
    -------
    lsst.afw.ImageF:  Image containing the mosaic.
    """
    butler = dp.Butler(repo)
    camera = butler.get('camera')
    image_source = RawImageSource(butler, visit)
    if det_names is None:
        det_names = [_.getName() for _ in camera]

    image = cgu.makeImageFromCamera(camera, detectorNameList=det_names,
                                    imageSource=image_source,
                                    imageFactory=afwImage.ImageF, binSize=bin_size)
    if outfile is not None:
        image.writeFits(outfile)

    return image
