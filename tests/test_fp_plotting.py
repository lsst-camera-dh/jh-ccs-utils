"""
Unit tests for generating focal plane "heat maps".
"""
import os
import unittest
import matplotlib.pyplot as plt
import siteUtils
from focalplane_plotting import plot_focal_plane
from lsst.obs.lsst.imsim import ImsimMapper

class PlotFocalPlaneTest(unittest.TestCase):
    """TestCase subclass for plot_focal_plane function."""
    def setUp(self):
        self.pngfile = 'focal_plane_mosaic_test_plot.png'

    def tearDown(self):
        if os.path.isfile(self.pngfile):
            os.remove(self.pngfile)

    def test_plot_focal_plane(self):
        """
        An operational test of generating a png image of the focal plane.
        """
        camera = ImsimMapper().camera
        run = '6549D'
        results = siteUtils.ETResults(run)
        gains = results.get_amp_data('fe55_BOT_analysis', 'gain')
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(1, 1, 1)
        plot_focal_plane(ax, gains, camera=camera, z_range=(0.8, 1.2))
        plt.savefig(self.pngfile)

if __name__ == '__main__':
    unittest.main()
