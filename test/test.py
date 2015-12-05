import unittest

class SimpleTest(unittest.TestCase):

    def test_math(self):
        self.assertEqual(1+1, 2)

if __name__ == '__main__':
    unittest.main()
