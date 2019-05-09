"""
Unit tests for generating focal plane "heat maps".
"""
import os
import unittest
from collections import defaultdict
import matplotlib.pyplot as plt
import siteUtils
from focalplane_plotting import plot_focal_plane
from lsst.obs.lsst.imsim import ImsimMapper

class PlotFocalPlaneTest(unittest.TestCase):
    """TestCase subclass for plot_focal_plane function."""
    def setUp(self):
        self.pngfile = 'focal_plane_mosaic_test_plot.png'
        self.camera = ImsimMapper().camera

    def tearDown(self):
        if os.path.isfile(self.pngfile):
            os.remove(self.pngfile)

    def test_plot_focal_plane(self):
        """
        An operational test of generating a png image of the focal plane.
        """
        run = '6549D'
        results = siteUtils.ETResults(run)
        gains = results.get_amp_data('fe55_BOT_analysis', 'gain')
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(1, 1, 1)
        plot_focal_plane(ax, gains, camera=self.camera, z_range=(0.5, 1.2))
        plt.savefig(self.pngfile)

    def test_amp_ccd_locations(self):
        """
        Fill specific locations with non-zero values to check mapping
        of rafts, ccds, and channels on the focalplane.
        """
        amp_data = defaultdict(dict)
        # lower left corner amp
        amp_data['R01_S00']['C00'] = 0.25
        # upper right corner amp
        amp_data['R43_S22']['C17'] = 1.
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(1, 1, 1)
        plot_focal_plane(ax, amp_data, camera=self.camera, z_range=(0, 2))
        outfile = 'test_amp_ccd_locations.png'
        plt.savefig(outfile)
        os.remove(outfile)

if __name__ == '__main__':
    unittest.main()
