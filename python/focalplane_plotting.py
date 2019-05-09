"""
Functions to plot amplifier-level quantities in the LSST focal plane.
"""
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
import lsst.afw.geom as afw_geom
from lsst.afw import cameraGeom
from lsst.obs.lsst.imsim import ImsimMapper

__all__ = ['plot_amp_boundaries', 'plot_det', 'plot_focal_plane']


def get_amp_patches(det, amps=None):
    """
    Return a list of Rectangle patches in focalplane coordinates
    corresponding to the amplifier segments in a detector object.

    Parameters
    ----------
    det: `lsst.afw.cameraGeom.detector.detector.Detector`
        Detector object.

    amps: container-type object [None]
        Python container that can be queried like `'C01 in amps'`
        to see if a particular channel is included for plotting.
        If None, then use all channels in det.

    Returns
    -------
    list of matplotlib.patches.Rectangle objects
    """
    transform = det.getTransform(cameraGeom.PIXELS, cameraGeom.FOCAL_PLANE)
    bbox = det['C01'].getBBox()
    dy, dx = bbox.getHeight(), bbox.getWidth()
    patches = []
    for amp in det:
        if amps is not None and amp.getName() not in amps:
            continue
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


def plot_det(ax, det, amp_values, cm=plt.cm.hot, z_range=None):
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
    z_range: 2-tuple of floats
        Minimum and maximum values into which to map the unit interval
        for the color map.  Value are mapped as
        max(0, min(1, (amp_value - z_range[0])/(z_range[1] - z_range[0])))
        If None, then use
        z_range = (min(amp_values.values()), max(amp_values.values()))

    Returns
    -------
    None
    """
    if z_range is None:
        zvals = amp_values.values()
        z_range = min(zvals), max(zvals)
    def mapped_value(amp_value):
        return max(0, min(1, ((amp_value - z_range[0])
                              /(z_range[1] - z_range[0]))))
    facecolors = [cm(mapped_value(amp_values[amp.getName()]))
                  for amp in det if amp.getName() in amp_values]
    patches = get_amp_patches(det, amp_values)
    pc = PatchCollection(patches, facecolors=facecolors)
    ax.add_collection(pc)


def plot_focal_plane(ax, amp_data, camera=None, cm=plt.cm.hot,
                     x_range=(-325, 325), y_range=(-325, 325),
                     zscale=1, z_range=None):
    if camera is None:
        camera = ImsimMapper().camera
    plot_amp_boundaries(ax)
    if z_range is None:
        amp_values = []
        for _ in amp_data.values():
            amp_values.extend(_.values())
        z_range = min(amp_values), max(amp_values)
    for det_name, amp_values in amp_data.items():
        plot_det(ax, camera[det_name], amp_values, cm=cm, z_range=z_range)
        max_amp_value = max(amp_values.values())
    plt.xlim(*x_range)
    plt.ylim(*y_range)
    plt.xlabel('y (mm)')
    plt.ylabel('x (mm)')
    norm = plt.Normalize(vmin=z_range[0], vmax=z_range[1])
    sm = plt.cm.ScalarMappable(cmap=cm, norm=norm)
    sm.set_array([])
    plt.colorbar(sm)
