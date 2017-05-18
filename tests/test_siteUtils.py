import os
import unittest
import siteUtils

class ParfileTestCase(unittest.TestCase):
    def setUp(self):
        "Write test parameter file that checks the casting mechanism."
        self.test_file = 'pars_test.txt'
        self.sections = ('Default', 'Case 1')
        self.values = {}
        self.values[self.sections[0]] = dict([('integer', 3),
                                              ('floating_point', 5e-4),
                                              ('string_value', 'foobar')])
        self.values[self.sections[1]] = dict([('integer', 5),
                                              ('floating_point', 126.1),
                                              ('string_value', 'test string')])
        output = open(self.test_file, 'w')
        for section in self.sections:
            output.write("[%s]\n" % section)
            for key, value in self.values[section].items():
                output.write("%s = %s\n" % (key, value))
        output.close()
    def tearDown(self):
        os.remove(self.test_file)
    def test_casting(self):
        for section in self.sections:
            pars = siteUtils.Parfile(self.test_file, section)
            for key, value in self.values[section].items():
                self.assertEquals(pars[key], value)

class PackageVersionSummaryTestCase(unittest.TestCase):
    """
    Test case class for parsing the summary.lims file for the package
    version info.
    """
    def setUp(self):
        pass
    def tearDown(self):
        pass
    def test_parse_package_versions_summary(self):
        "Test that the expected package versions are returned."
        summary_lims_file = os.path.join(os.environ['HARNESSEDJOBSDIR'],
                                         'tests', 'summary_lims_test_file')
        versions = siteUtils.parse_package_versions_summary(summary_lims_file)
        self.assertEqual(versions['harnessed-jobs'], '0.4.28')
        self.assertEqual(versions['lcatr-harness'], '0.13.0')
        self.assertEqual(versions['eTraveler-clientAPI'], '1.2.2')
        self.assertEqual(versions['datacat_config'],
                         "/nfs/farm/g/lsst/u1/software/datacat/config.cfg")
        self.assertEqual(len(versions), 11)

class PngDataProductTestCase(unittest.TestCase):
    "TestCase class for png data product handling code."
    def setUp(self):
        pass
    def tearDown(self):
        pass
    def test_png_data_product(self):
        data_product = 'median_dark'
        lsst_num = 'E2V-CCD250-264'

        run_number = '4005D'
        os.environ['LCATR_RUN_NUMBER'] = run_number
        pngfile = '%s_%s_%s.png' % (lsst_num, run_number, data_product)
        self.assertEqual(siteUtils.png_data_product(pngfile, lsst_num),
                         data_product)

        del os.environ['LCATR_RUN_NUMBER']
        pngfile = '%s_%s.png' % (lsst_num, data_product)
        self.assertEqual(siteUtils.png_data_product(pngfile, lsst_num),
                         data_product)

if __name__ == '__main__':
    unittest.main()
