"""
Module to make mosaics of raw CCD FITS files in the LSST focal
plane using the tools in lsst.afw.cameraGeom and the focal plane
layout in obs_lsst.
"""
import copy
import numpy as np
import lsst.afw.image as afwImage
from lsst.afw.cameraGeom import utils as cgu
import lsst.daf.persistence as dp

__all__ = ['RawImageSource']


class RawImageSource:
    """
    ImageSource class to pass to the cameraGeom.makeImageFromCamera
    function to make focal plane mosaics.
    """
    ix = np.concatenate((np.arange(8), np.arange(7, -1, -1)))
    iy = np.concatenate((np.zeros(8, dtype=int), np.ones(8, dtype=int)))
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

    def getCcdImage(self, detector, imageFactory, binSize):
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
        binSize: int
            Not used. This is needed for interface compatibility with
            the cameraGeom code.

        Returns
        -------
        (lsst.afw.Image, )
        """
        image = imageFactory(detector.getBBox())
        datarefs = self.butler.subset('raw_amp', visit=self.visit,
                                      detector=detector.getId())
        for dataref, amp_info in zip(datarefs, detector):
            hdu = amp_info.get('hdu')
            raw_bbox = amp_info.getRawDataBBox()
            dx = raw_bbox.getWidth()
            dy = raw_bbox.getHeight()
            full_segment = dataref.get('raw_amp').getImage()
            imaging_segment = imageFactory(full_segment, raw_bbox)
            xoffset = self.ix[hdu-1]*dx
            yoffset = self.iy[hdu-1]*dy
            data = copy.deepcopy(imaging_segment.array)
            if amp_info.getRawFlipX():
                data = data[:, ::-1]
            if amp_info.getRawFlipY():
                data = data[::-1, :]
            image.array[yoffset: yoffset + dy, xoffset: xoffset + dx] += data
        return (image, )


def make_fp_mosaic(repo, visit, det_names=None, outfile=None):
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
                                    imageFactory=afwImage.ImageF)
    if outfile is not None:
        image.writeFits(outfile)

    return image
