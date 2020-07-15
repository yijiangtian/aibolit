# The MIT License (MIT)
#
# Copyright (c) 2020 Aibolit
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import os
import pickle
from pathlib import Path
from unittest import TestCase

import numpy as np
import pandas as pd

from aibolit.config import Config
from aibolit.model.stats import Stats


class TestStats(TestCase):

    def __init__(self, *args, **kwargs):
        super(TestStats, self).__init__(*args, **kwargs)
        self.cur_file_dir = Path(os.path.realpath(__file__)).parent
        self.config = Config.get_patterns_config()

    def test_get_minimum(self):
        minimum_arr = Stats.get_minimum([0, 0.23, 0.45], [0.34, 0.01, 0.37], [0.01, 0.50, 0.2])
        self.assertTrue(np.array_equal(minimum_arr[0], np.array([0, 0.01, 0.2])))
        self.assertTrue(np.array_equal(minimum_arr[1], np.array([0, 1, 2])))

    def test_get_array(self):
        lst = [np.array([0, 1, 2, 3, 4, 5], dtype=float),
               np.array([0, 1, 2, 3, 3, 3], dtype=float)]
        x = np.array(lst)
        mask = x > 0
        ncss = np.array([0.01, 0.02])
        res = Stats.get_array(x, mask, 2, ncss)
        self.assertTrue(
            np.array_equal(
                res,
                np.array([[0., 1., 2.01, 3., 4., 5.],
                          [0., 1., 2.02, 3., 3., 3.]])
            )
        )

    def test_divide_array(self):
        x = [[0, 0, 0], [0, 0, 1], [1, 1, 2]]
        nulls, not_nulls = Stats.divide_array(x, 2)
        self.assertTrue(np.array_equal(nulls[0], np.array([0, 0, 0])))
        self.assertTrue(np.array_equal(not_nulls[0], np.array([0, 0, 1])))
        self.assertTrue(np.array_equal(not_nulls[1], np.array([1, 1, 2])))

    def __load_mock_model(self):
        load_model_file = Path(self.cur_file_dir, 'model.pkl')
        with open(load_model_file, 'rb') as fid:
            model = pickle.load(fid)
            return model

    def test_stat_aibolit_pipeline(self):
        model = self.__load_mock_model()
        test_csv = Path(self.cur_file_dir, 'test_dataset.csv')
        test_df = pd.read_csv(test_csv)
        table = Stats.aibolit_stat(test_df, model)
        test_csv = Path(self.cur_file_dir, 'results_test.csv')
        results_df = pd.read_csv(test_csv, index_col=0)
        all_elements_compared: pd.DataFrame = table.eq(results_df)
        are_equal = np.equal.reduce(np.ravel(all_elements_compared.values))
        self.assertTrue(are_equal)
