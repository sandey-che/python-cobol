#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, './../python-cobol')

import cobol
import unittest


class PythonCobolTest(unittest.TestCase):
    def test(self):
        with open("example.cbl",'r') as f:
            rows = cobol.process_cobol(f.readlines())
        
        self.assertEqual(rows[0]['name'], 'EXAMPLE_GROUP')
        self.assertEqual(rows[1]['name'], 'FIELD_2_1')
        self.assertEqual(rows[2]['name'], 'FIELD_3_1_1')
        self.assertEqual(rows[3]['name'], 'FIELD_3_1_2')
        self.assertEqual(rows[4]['name'], 'FIELD_2_2')
        self.assertEqual(rows[5]['name'], 'FIELD_3_2_1')
        self.assertEqual(rows[6]['name'], 'FIELD_3_2_2')
        self.assertEqual(rows[7]['name'], 'FIELD_2_3')
        self.assertEqual(rows[8]['name'], 'FIELD_3_3_1')
        self.assertEqual(rows[9]['name'], 'FIELD_3_3_2')
        self.assertEqual(rows[10]['name'], 'THIS_IS_ANOTHER_GROUP')
        self.assertEqual(rows[11]['name'], 'YES')


if __name__ == '__main__':
    unittest.main()
