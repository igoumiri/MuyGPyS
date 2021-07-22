# Copyright 2021 Lawrence Livermore National Security, LLC and other MuyGPyS
# Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import numpy as np

from absl.testing import absltest
from absl.testing import parameterized

from MuyGPyS.examples.classify import example_lambdas, make_masks, do_uq
from MuyGPyS.gp.muygps import MuyGPS
from MuyGPyS.neighbors import NN_Wrapper
from MuyGPyS.optimize.batch import (
    get_balanced_batch,
    sample_batch,
    sample_balanced_batch,
    full_filtered_batch,
)
from MuyGPyS.predict import classify_any, classify_two_class_uq
from MuyGPyS.testing.test_utils import (
    _make_gaussian_matrix,
    _make_gaussian_dict,
    _make_gaussian_data,
    _basic_nn_kwarg_options,
)
from MuyGPyS.uq import (
    train_two_class_interval,
)


class ClassifyTest(parameterized.TestCase):
    @parameterized.parameters(
        (
            (1000, 200, f, r, nn, nn_kwargs, k_kwargs)
            for f in [100, 10, 2]
            for r in [10, 2, 1]
            for nn in [5, 10, 100]
            for nn_kwargs in _basic_nn_kwarg_options
            # for f in [100]
            # for r in [10]
            # for nn in [10]
            # for nn_kwargs in _basic_nn_kwarg_options
            for k_kwargs in (
                {
                    "kern": "matern",
                    "eps": {"val": 1e-5},
                    "nu": {"val": 0.38},
                    "length_scale": {"val": 1.5},
                },
            )
        )
    )
    def test_classify_any(
        self,
        train_count,
        test_count,
        feature_count,
        response_count,
        nn_count,
        nn_kwargs,
        k_kwargs,
    ):
        muygps = MuyGPS(**k_kwargs)

        train, test = _make_gaussian_data(
            train_count,
            test_count,
            feature_count,
            response_count,
            categorical=True,
        )
        nbrs_lookup = NN_Wrapper(train["input"], nn_count, **nn_kwargs)

        predictions, _ = classify_any(
            muygps,
            test["input"],
            train["input"],
            nbrs_lookup,
            train["output"],
        )
        self.assertEqual(predictions.shape, (test_count, response_count))

    @parameterized.parameters(
        (
            (1000, 200, f, r, nn, b, nn_kwargs, k_kwargs)
            # for f in [100]
            # for r in [2]
            # for nn in [10]
            # for b in [200]
            for f in [100, 10, 2]
            for r in [2]
            for nn in [5, 10, 100]
            for b in [200]
            for nn_kwargs in _basic_nn_kwarg_options
            for k_kwargs in (
                {
                    "kern": "matern",
                    "eps": {"val": 1e-5},
                    "nu": {"val": 0.38},
                    "length_scale": {"val": 1.5},
                },
                {
                    "kern": "rbf",
                    "eps": {"val": 1e-5},
                    "length_scale": {"val": 1.5},
                },
            )
        )
    )
    def test_classify_uq(
        self,
        train_count,
        test_count,
        feature_count,
        response_count,
        nn_count,
        batch_count,
        nn_kwargs,
        k_kwargs,
    ):
        muygps = MuyGPS(**k_kwargs)

        objective_count = len(example_lambdas)
        train, test = _make_gaussian_data(
            train_count,
            test_count,
            feature_count,
            response_count,
            categorical=True,
        )
        train["output"] *= 2
        test["output"] *= 2
        nbrs_lookup = NN_Wrapper(train["input"], nn_count, **nn_kwargs)

        predictions, variances, _ = classify_two_class_uq(
            muygps,
            test["input"],
            train["input"],
            nbrs_lookup,
            train["output"],
        )

        self.assertEqual(predictions.shape, (test_count, response_count))
        self.assertEqual(variances.shape, (test_count,))

        train_labels = np.argmax(train["output"], axis=1)
        indices, nn_indices = get_balanced_batch(
            nbrs_lookup,
            train_labels,
            batch_count,
        )

        cutoffs = train_two_class_interval(
            muygps,
            indices,
            nn_indices,
            train["input"],
            train["output"],
            train_labels,
            example_lambdas,
        )
        self.assertEqual(cutoffs.shape, (objective_count,))

        min_label = np.min(train["output"][0, :])
        max_label = np.max(train["output"][0, :])
        if min_label == 0.0 and max_label == 1.0:
            predicted_labels = np.argmax(predictions, axis=1)
        elif min_label == -1.0 and max_label == 1.0:
            predicted_labels = 2 * np.argmax(predictions, axis=1) - 1
        else:
            raise ("Unhandled label encoding min ({min_label}, {max_label})!")
        mid_value = (min_label + max_label) / 2

        masks = make_masks(predictions, cutoffs, variances, mid_value)
        self.assertEqual(masks.shape, (objective_count, test_count))

        acc, uq = do_uq(predictions, test["output"], masks)
        self.assertGreaterEqual(acc, 0.0)
        self.assertLessEqual(acc, 1.0)
        self.assertEqual(uq.shape, (objective_count, 3))


if __name__ == "__main__":
    absltest.main()
