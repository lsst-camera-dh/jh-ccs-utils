"Unit tests for ccsTools module."
import os
import unittest
import ccsTools

class CcsSubsystemMappingTestCase(unittest.TestCase):
    "TestCase class for ccs_subsystem_mapping function."

    def setUp(self):
        self.config_file = 'ccs_subsystems.cfg'
        with open(self.config_file, 'w') as output:
            output.write('[ccs_subsystems]\n')
            output.write('ts8 = ts8\n')
            output.write('ts = ts\n')
            output.write('pd = ts/PhotoDiode\n')
            output.write('mono = ts/Monochromator\n')
            output.write('rebps = ccs-rebps\n')

    def tearDown(self):
        try:
            os.remove(self.config_file)
        except OSError:
            pass

    def test_ccs_subsystem_mapping(self):
        "Test code for ccs_subsystem_mapping function."
        os.environ['LCATR_CCS_SUBSYSTEM_CONFIG'] = self.config_file
        mapping = ccsTools.ccs_subsystem_mapping()
        self.assertEqual(set(mapping.keys()),
                         set('ts8 ts pd mono rebps'.split()))
        self.assertEqual(mapping['ts8'], 'ts8')
        self.assertEqual(mapping['ts'], 'ts')
        self.assertEqual(mapping['pd'], 'ts/PhotoDiode')
        self.assertEqual(mapping['mono'], 'ts/Monochromator')
        self.assertEqual(mapping['rebps'], 'ccs-rebps')

        del os.environ['LCATR_CCS_SUBSYSTEM_CONFIG']
        self.assertEqual(None, ccsTools.ccs_subsystem_mapping())

        mapping = ccsTools.ccs_subsystem_mapping(self.config_file)
        self.assertEqual(set(mapping.keys()),
                         set('ts8 ts pd mono rebps'.split()))
        self.assertEqual(mapping['ts8'], 'ts8')
        self.assertEqual(mapping['ts'], 'ts')
        self.assertEqual(mapping['pd'], 'ts/PhotoDiode')
        self.assertEqual(mapping['mono'], 'ts/Monochromator')
        self.assertEqual(mapping['rebps'], 'ccs-rebps')

if __name__ == '__main__':
    unittest.main()
