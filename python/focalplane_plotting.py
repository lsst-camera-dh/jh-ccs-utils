"""
Functions to plot amplifier-level quantities in the LSST focal plane.
"""
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
import lsst.afw.geom as afw_geom
from lsst.afw import cameraGeom
from lsst.obs.lsst.imsim import ImsimMapper

__all__ = ['plot_amp_boundaries', 'plot_det']


def get_amp_patches(det):
    """
    Return a list of Rectangle patches in focalplane coordinates
    corresponding to the amplifier segments in a detector object.

    Parameters
    ----------
    det: `lsst.afw.cameraGeom.detector.detector.Detector`
        Detector object.

    Returns
    -------
    list of matplotlib.patches.Rectangle objects
    """
    transform = det.getTransform(cameraGeom.PIXELS, cameraGeom.FOCAL_PLANE)
    bbox = det['C01'].getBBox()
    dy, dx = bbox.getHeight(), bbox.getWidth()
    patches = []
    for amp in det:
        j, i = tuple(int(_) for _ in amp.getName()[1:])
        y, x = j*dy, i*dx
        x0, y0 = transform.applyForward(afw_geom.Point2D(x, y))
        x1, y1 = transform.applyForward(afw_geom.Point2D(x + dx, y + dy))
        patches.append(Rectangle((x0, y0), x1 - x0, y1 - y0))
    return patches


def plot_amp_boundaries(ax, camera=None, edgecolor='blue', facecolor='white'):
    """
    Plot the amplifier boundaries for all of the detectors in a camera.

    Parameters
    ----------
    ax: `matplotlib.Axes`
        Axes object used to render the patch collection containing
        the amplifier boundary Rectangles.
    camera: `lsst.afw.cameraGeom.camera.camera.Camera` [None]
        Camera object containing the detector info. If None, use
        `lsst.obs.lsst.imsim.ImsimMapper().camera`
    edgecolor: str or tuple of RGBA values ["blue"]
        Color used to draw outline of amplifiers.
    facecolor: str or tuple of RGBA values ["white"]
        Color used to render the Rectangle corresponding to the
        amplifier region.

    Returns
    -------
    None
    """
    if camera is None:
        camera = ImsimMapper().camera
    patches = []
    for det in camera:
        patches.extend(get_amp_patches(det))
    pc = PatchCollection(patches, edgecolor=edgecolor, facecolor=facecolor)
    ax.add_collection(pc)


def plot_det(ax, det, amp_values, cm=plt.cm.hot):
    """
    Plot the amplifiers in a detector, rendering each amplier region with
    a color corresponding to its assigned value.

    Parameters
    ----------
    ax: `matplotlib.Axes`
        Axes object used to render the patch collection containing
        the amplifier boundary Rectangles.
    det: `lsst.afw.cameraGeom.detector.detector.Detector`
        Detector object.
    amp_values: dict of floats
        Dictionary of amplifier values to render, keyed by channel ID,
        e.g., 'C00', 'C01', etc.
    cm: `matplotlib.colors.Colormap`
        Colormap used to render amplifier values.

    Returns
    -------
    None
    """
    facecolors = [cm(amp_values[amp.getName()]) for amp in det]
    patches = get_amp_patches(det)
    pc = PatchCollection(patches, facecolors=facecolors)
    ax.add_collection(pc)
