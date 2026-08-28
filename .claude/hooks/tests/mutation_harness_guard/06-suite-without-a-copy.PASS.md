# An ordinary test file runs a suite and copies nothing. -> PASS.
TOOL_NAME="Write"
FILE_PATH="plugins/psford-tickets/tests/test_thing.py"
CONTENT='import unittest
class T(unittest.TestCase):
    def test_it(self): self.assertTrue(True)'
