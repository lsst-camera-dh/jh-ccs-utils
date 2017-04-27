"Unit tests for ccs_scripting_tools module."
import unittest
import io
import logging
import ccs_scripting_tools

class FileStreamProxy(object):
    "In-memory file-like stream class to use with unit tests."
    def __init__(self):
        self.output = io.StringIO()

    def write(self, phrase):
        """
        Write the phrase to the underlying StringIO object, first casting
        as a unicode.
        """
        self.output.write(unicode(phrase))

    def get_value(self):
        """
        Return the current stream, close the StringIO object, and
        create a new one for the next (set of) write(s).
        """
        value = self.output.getvalue()
        self.output.close()
        self.output = io.StringIO()
        return value

class CcsSubsystemsTestCase(unittest.TestCase):
    "TestCase subclass for testing the CcsSubsystems class."
    def test_interface(self):
        sub = ccs_scripting_tools.CcsSubsystems(dict(ts8='ts8',
                                                     pd='ts/PhotoDiode',
                                                     mono='ts/Monochromator'))
        self.assertTrue(hasattr(sub, 'ts8'))
        self.assertTrue(hasattr(sub, 'pd'))
        self.assertTrue(hasattr(sub, 'mono'))

class SubsystemDecoratorTestCase(unittest.TestCase):
    "TestCase subclass for SubsystemDecorator."
    def test_logging(self):
        fs = FileStreamProxy()
        logging.basicConfig(format="%(message)s",
                            level=logging.INFO,
                            stream=fs)
        logger = logging.getLogger()
        sub = ccs_scripting_tools.CcsSubsystems(dict(ts8='ts8',
                                                     pd='ts/PhotoDiode',
                                                     mono='ts/Monochromator'),
                                                logger=logger)
        sub.ts8.synchCommand(10, "setTestType FE55")
        self.assertEqual(fs.get_value(), '10 setTestType FE55\n')
        sub.ts8.synchCommand(10, "setTestType", "FE55")
        self.assertEqual(fs.get_value(), '10 setTestType FE55\n')
        sub.ts8.asynchCommand("setTestType", "FE55")
        self.assertEqual(fs.get_value(), 'setTestType FE55\n')

if __name__ == '__main__':
    unittest.main()
