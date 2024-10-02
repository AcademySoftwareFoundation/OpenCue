import unittest

def create_test_suite():
    loader = unittest.TestLoader()
    start_dir = '.'  # Specify the directory where your test files reside
    suite = loader.discover(start_dir, pattern='*_test.py')
    return suite

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    test_suite = create_test_suite()
    runner.run(test_suite)