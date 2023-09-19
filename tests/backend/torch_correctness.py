# Copyright 2021-2022 Lawrence Livermore National Security, LLC and other
# MuyGPyS Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: MIT

from absl.testing import absltest
from absl.testing import parameterized

import MuyGPyS._src.math.numpy as np
import MuyGPyS._src.math.torch as torch
from MuyGPyS import config
from MuyGPyS._src.gp.tensors.numpy import (
    _pairwise_tensor as pairwise_tensor_n,
    _crosswise_tensor as crosswise_tensor_n,
    _make_train_tensors as make_train_tensors_n,
    _make_fast_predict_tensors as make_fast_predict_tensors_n,
    _fast_nn_update as fast_nn_update_n,
    _F2 as F2_n,
    _l2 as l2_n,
)
from MuyGPyS._src.gp.tensors.torch import (
    _pairwise_tensor as pairwise_tensor_t,
    _crosswise_tensor as crosswise_tensor_t,
    _make_train_tensors as make_train_tensors_t,
    _make_fast_predict_tensors as make_fast_predict_tensors_t,
    _fast_nn_update as fast_nn_update_t,
    _F2 as F2_t,
    _l2 as l2_t,
)
from MuyGPyS._src.gp.kernels.numpy import (
    _rbf_fn as rbf_fn_n,
    _matern_05_fn as matern_05_fn_n,
    _matern_15_fn as matern_15_fn_n,
    _matern_25_fn as matern_25_fn_n,
    _matern_inf_fn as matern_inf_fn_n,
    _matern_gen_fn as matern_gen_fn_n,
)
from MuyGPyS._src.gp.kernels.torch import (
    _rbf_fn as rbf_fn_t,
    _matern_05_fn as matern_05_fn_t,
    _matern_15_fn as matern_15_fn_t,
    _matern_25_fn as matern_25_fn_t,
    _matern_inf_fn as matern_inf_fn_t,
    _matern_gen_fn as matern_gen_fn_t,
)
from MuyGPyS._src.gp.muygps.numpy import (
    _muygps_posterior_mean as muygps_posterior_mean_n,
    _muygps_diagonal_variance as muygps_diagonal_variance_n,
    _muygps_fast_posterior_mean as muygps_fast_posterior_mean_n,
    _mmuygps_fast_posterior_mean as mmuygps_fast_posterior_mean_n,
    _muygps_fast_posterior_mean_precompute as muygps_fast_posterior_mean_precompute_n,
)
from MuyGPyS._src.gp.muygps.torch import (
    _muygps_posterior_mean as muygps_posterior_mean_t,
    _muygps_diagonal_variance as muygps_diagonal_variance_t,
    _muygps_fast_posterior_mean as muygps_fast_posterior_mean_t,
    _mmuygps_fast_posterior_mean as mmuygps_fast_posterior_mean_t,
    _muygps_fast_posterior_mean_precompute as muygps_fast_posterior_mean_precompute_t,
)
from MuyGPyS._src.gp.noise.numpy import (
    _homoscedastic_perturb as homoscedastic_perturb_n,
    _heteroscedastic_perturb as heteroscedastic_perturb_n,
)
from MuyGPyS._src.gp.noise.torch import (
    _homoscedastic_perturb as homoscedastic_perturb_t,
    _heteroscedastic_perturb as heteroscedastic_perturb_t,
)
from MuyGPyS._src.optimize.loss.torch import (
    _mse_fn as mse_fn_t,
    _cross_entropy_fn as cross_entropy_fn_t,
    _lool_fn as lool_fn_t,
    _pseudo_huber_fn as pseudo_huber_fn_t,
    _looph_fn as looph_fn_t,
)
from MuyGPyS._src.optimize.sigma_sq.numpy import (
    _analytic_sigma_sq_optim as analytic_sigma_sq_optim_n,
)
from MuyGPyS._src.optimize.sigma_sq.torch import (
    _analytic_sigma_sq_optim as analytic_sigma_sq_optim_t,
)
from MuyGPyS._test.utils import (
    _exact_nn_kwarg_options,
    _make_gaussian_matrix,
    _make_gaussian_data,
    _make_heteroscedastic_test_nugget,
)
from MuyGPyS.gp import MuyGPS, MultivariateMuyGPS as MMuyGPS

from MuyGPyS.gp.distortion import (
    apply_distortion,
    AnisotropicDistortion,
    IsotropicDistortion,
)
from MuyGPyS.gp.hyperparameter import ScalarHyperparameter
from MuyGPyS.gp.kernels import Matern
from MuyGPyS.gp.noise import HeteroscedasticNoise, HomoscedasticNoise
from MuyGPyS.neighbors import NN_Wrapper
from MuyGPyS.optimize.batch import sample_batch
from MuyGPyS.optimize.loss import (
    LossFn,
    mse_fn as mse_fn_n,
    cross_entropy_fn as cross_entropy_fn_n,
    lool_fn as lool_fn_n,
    pseudo_huber_fn as pseudo_huber_fn_n,
    looph_fn as looph_fn_n,
    make_raw_predict_and_loss_fn,
    make_var_predict_and_loss_fn,
)
from MuyGPyS.optimize.objective import make_loo_crossval_fn
from MuyGPyS.optimize.sigma_sq import make_analytic_sigma_sq_optim

if config.state.torch_enabled is False:
    raise ValueError("Bad attempt to run torch-only code with torch diabled.")
if config.state.backend == "mpi":
    raise ValueError("Bad attempt to run non-MPI code in MPI mode.")
if config.state.backend != "numpy":
    raise ValueError(
        f"torch_correctness.py must be run in numpy mode, not "
        f"{config.state.backend} mode."
    )

# make torch loss functor aliases
mse_fn_t = LossFn(mse_fn_t, make_raw_predict_and_loss_fn)
cross_entropy_fn_t = LossFn(cross_entropy_fn_t, make_raw_predict_and_loss_fn)
lool_fn_t = LossFn(lool_fn_t, make_var_predict_and_loss_fn)
pseudo_huber_fn_t = LossFn(pseudo_huber_fn_t, make_raw_predict_and_loss_fn)
looph_fn_t = LossFn(looph_fn_t, make_var_predict_and_loss_fn)


def isotropic_F2_n(diffs, length_scale):
    return F2_n(diffs / length_scale)


def isotropic_l2_n(diffs, length_scale):
    return l2_n(diffs / length_scale)


def isotropic_F2_t(diffs, length_scale):
    return F2_t(diffs / length_scale)


def isotropic_l2_t(diffs, length_scale):
    return l2_t(diffs / length_scale)


def anisotropic_F2_n(diffs, **length_scales):
    length_scale_array = AnisotropicDistortion._get_length_scale_array(
        np.array, diffs.shape, **length_scales
    )
    return F2_n(diffs / length_scale_array)


def anisotropic_l2_n(diffs, **length_scales):
    length_scale_array = AnisotropicDistortion._get_length_scale_array(
        np.array, diffs.shape, **length_scales
    )
    return l2_n(diffs / length_scale_array)


def anisotropic_F2_t(diffs, **length_scales):
    length_scale_array = AnisotropicDistortion._get_length_scale_array(
        torch.array, diffs.shape, **length_scales
    )
    return F2_t(diffs / length_scale_array)


def anisotropic_l2_t(diffs, **length_scales):
    length_scale_array = AnisotropicDistortion._get_length_scale_array(
        torch.array, diffs.shape, **length_scales
    )
    return l2_t(diffs / length_scale_array)


rbf_isotropic_fn_n = apply_distortion(isotropic_F2_n, length_scale=1.0)(
    rbf_fn_n
)
matern_05_isotropic_fn_n = apply_distortion(isotropic_l2_n, length_scale=1.0)(
    matern_05_fn_n
)
matern_15_isotropic_fn_n = apply_distortion(isotropic_l2_n, length_scale=1.0)(
    matern_15_fn_n
)
matern_25_isotropic_fn_n = apply_distortion(isotropic_l2_n, length_scale=1.0)(
    matern_25_fn_n
)
matern_inf_isotropic_fn_n = apply_distortion(isotropic_l2_n, length_scale=1.0)(
    matern_inf_fn_n
)
matern_gen_isotropic_fn_n = apply_distortion(isotropic_l2_n, length_scale=1.0)(
    matern_gen_fn_n
)

rbf_isotropic_fn_t = apply_distortion(isotropic_F2_t, length_scale=1.0)(
    rbf_fn_t
)
matern_05_isotropic_fn_t = apply_distortion(isotropic_l2_t, length_scale=1.0)(
    matern_05_fn_t
)
matern_15_isotropic_fn_t = apply_distortion(isotropic_l2_t, length_scale=1.0)(
    matern_15_fn_t
)
matern_25_isotropic_fn_t = apply_distortion(isotropic_l2_t, length_scale=1.0)(
    matern_25_fn_t
)
matern_inf_isotropic_fn_t = apply_distortion(isotropic_l2_t, length_scale=1.0)(
    matern_inf_fn_t
)
matern_gen_isotropic_fn_t = apply_distortion(isotropic_l2_t, length_scale=1.0)(
    matern_gen_fn_t
)

rbf_anisotropic_fn_n = apply_distortion(anisotropic_F2_n, length_scale0=1.0)(
    rbf_fn_n
)
matern_05_anisotropic_fn_n = apply_distortion(
    anisotropic_l2_n, length_scale0=1.0
)(matern_05_fn_n)
matern_15_anisotropic_fn_n = apply_distortion(
    anisotropic_l2_n, length_scale0=1.0
)(matern_15_fn_n)
matern_25_anisotropic_fn_n = apply_distortion(
    anisotropic_l2_n, length_scale0=1.0
)(matern_25_fn_n)
matern_inf_anisotropic_fn_n = apply_distortion(
    anisotropic_l2_n, length_scale0=1.0
)(matern_inf_fn_n)
matern_gen_anisotropic_fn_n = apply_distortion(
    anisotropic_l2_n, length_scale0=1.0
)(matern_gen_fn_n)

rbf_anisotropic_fn_t = apply_distortion(anisotropic_F2_t, length_scale0=1.0)(
    rbf_fn_t
)
matern_05_anisotropic_fn_t = apply_distortion(
    anisotropic_l2_t, length_scale0=1.0
)(matern_05_fn_t)
matern_15_anisotropic_fn_t = apply_distortion(
    anisotropic_l2_t, length_scale0=1.0
)(matern_15_fn_t)
matern_25_anisotropic_fn_t = apply_distortion(
    anisotropic_l2_t, length_scale0=1.0
)(matern_25_fn_t)
matern_inf_anisotropic_fn_t = apply_distortion(
    anisotropic_l2_t, length_scale0=1.0
)(matern_inf_fn_t)
matern_gen_anisotropic_fn_t = apply_distortion(
    anisotropic_l2_t, length_scale0=1.0
)(matern_gen_fn_t)


def _allclose(x, y) -> bool:
    return np.allclose(
        x, y, atol=1e-5 if config.state.low_precision() else 1e-8
    )


class TensorsTestCase(parameterized.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TensorsTestCase, cls).setUpClass()
        cls.train_count = 1000
        cls.test_count = 100
        cls.feature_count = 10
        cls.response_count = 1
        cls.nn_count = 40
        cls.batch_count = 500
        cls.length_scale = 1.0
        cls.nu = 0.5
        cls.nu_bounds = (1e-1, 1e1)
        cls.eps = 1e-3
        cls.eps_heteroscedastic_n = _make_heteroscedastic_test_nugget(
            cls.batch_count, cls.nn_count, cls.eps
        )
        cls.eps_heteroscedastic_train_n = _make_heteroscedastic_test_nugget(
            cls.train_count, cls.nn_count, cls.eps
        )
        cls.eps_heteroscedastic_t = torch.ndarray(cls.eps_heteroscedastic_n)
        cls.eps_heteroscedastic_train_t = torch.ndarray(
            cls.eps_heteroscedastic_train_n
        )
        cls.train_features_n = _make_gaussian_matrix(
            cls.train_count, cls.feature_count
        )
        cls.train_features_t = torch.from_numpy(cls.train_features_n)
        cls.train_responses_n = _make_gaussian_matrix(
            cls.train_count, cls.response_count
        )
        cls.train_responses_t = torch.from_numpy(cls.train_responses_n)
        cls.test_features_n = _make_gaussian_matrix(
            cls.test_count, cls.feature_count
        )
        cls.test_features_t = torch.from_numpy(cls.test_features_n)
        cls.test_responses_n = _make_gaussian_matrix(
            cls.test_count, cls.response_count
        )
        cls.test_responses_t = torch.from_numpy(cls.test_responses_n)
        cls.nbrs_lookup = NN_Wrapper(
            cls.train_features_n, cls.nn_count, **_exact_nn_kwarg_options[0]
        )
        cls.muygps_n = MuyGPS(
            kernel=Matern(
                nu=ScalarHyperparameter(cls.nu, cls.nu_bounds),
                metric=IsotropicDistortion(
                    l2_n, length_scale=ScalarHyperparameter(cls.length_scale)
                ),
            ),
            eps=HomoscedasticNoise(
                cls.eps, _backend_fn=homoscedastic_perturb_n
            ),
            _backend_mean_fn=muygps_posterior_mean_n,
            _backend_var_fn=muygps_diagonal_variance_n,
            _backend_fast_mean_fn=muygps_fast_posterior_mean_n,
            _backend_fast_precompute_fn=muygps_fast_posterior_mean_precompute_n,
            _backend_ones=np.ones,
            _backend_ndarray=np.ndarray,
            _backend_ftype=np.ftype,
            _backend_farray=np.farray,
            _backend_outer=np.outer,
        )
        cls.muygps_t = MuyGPS(
            kernel=Matern(
                nu=ScalarHyperparameter(cls.nu, cls.nu_bounds),
                metric=IsotropicDistortion(
                    l2_n, length_scale=ScalarHyperparameter(cls.length_scale)
                ),
            ),
            eps=HomoscedasticNoise(
                cls.eps, _backend_fn=homoscedastic_perturb_t
            ),
            _backend_mean_fn=muygps_posterior_mean_t,
            _backend_var_fn=muygps_diagonal_variance_t,
            _backend_fast_mean_fn=muygps_fast_posterior_mean_t,
            _backend_fast_precompute_fn=muygps_fast_posterior_mean_precompute_t,
            _backend_ones=torch.ones,
            _backend_ndarray=torch.ndarray,
            _backend_ftype=torch.ftype,
            _backend_farray=torch.farray,
            _backend_outer=torch.outer,
        )
        cls.muygps_heteroscedastic_n = MuyGPS(
            kernel=Matern(
                nu=ScalarHyperparameter(cls.nu, cls.nu_bounds),
                metric=IsotropicDistortion(
                    l2_n, length_scale=ScalarHyperparameter(cls.length_scale)
                ),
            ),
            eps=HeteroscedasticNoise(
                cls.eps_heteroscedastic_n, _backend_fn=heteroscedastic_perturb_n
            ),
            _backend_mean_fn=muygps_posterior_mean_n,
            _backend_var_fn=muygps_diagonal_variance_n,
            _backend_fast_mean_fn=muygps_fast_posterior_mean_n,
            _backend_fast_precompute_fn=muygps_fast_posterior_mean_precompute_n,
            _backend_ones=np.ones,
            _backend_ndarray=np.ndarray,
            _backend_ftype=np.ftype,
            _backend_farray=np.farray,
            _backend_outer=np.outer,
        )
        cls.muygps_heteroscedastic_t = MuyGPS(
            kernel=Matern(
                nu=ScalarHyperparameter(cls.nu, cls.nu_bounds),
                metric=IsotropicDistortion(
                    l2_n, length_scale=ScalarHyperparameter(cls.length_scale)
                ),
            ),
            eps=HeteroscedasticNoise(
                cls.eps_heteroscedastic_t, _backend_fn=heteroscedastic_perturb_t
            ),
            _backend_mean_fn=muygps_posterior_mean_t,
            _backend_var_fn=muygps_diagonal_variance_t,
            _backend_fast_mean_fn=muygps_fast_posterior_mean_t,
            _backend_fast_precompute_fn=muygps_fast_posterior_mean_precompute_t,
            _backend_ones=torch.ones,
            _backend_ndarray=torch.ndarray,
            _backend_ftype=torch.ftype,
            _backend_farray=torch.farray,
            _backend_outer=torch.outer,
        )
        cls.muygps_heteroscedastic_train_n = MuyGPS(
            kernel=Matern(
                nu=ScalarHyperparameter(cls.nu, cls.nu_bounds),
                metric=IsotropicDistortion(
                    l2_n, length_scale=ScalarHyperparameter(cls.length_scale)
                ),
            ),
            eps=HeteroscedasticNoise(
                cls.eps_heteroscedastic_train_n,
                _backend_fn=heteroscedastic_perturb_n,
            ),
            _backend_mean_fn=muygps_posterior_mean_n,
            _backend_var_fn=muygps_diagonal_variance_n,
            _backend_fast_mean_fn=muygps_fast_posterior_mean_n,
            _backend_fast_precompute_fn=muygps_fast_posterior_mean_precompute_n,
            _backend_math=np,
        )
        cls.muygps_heteroscedastic_train_t = MuyGPS(
            kernel=Matern(
                nu=ScalarHyperparameter(cls.nu, cls.nu_bounds),
                metric=IsotropicDistortion(
                    l2_n, length_scale=ScalarHyperparameter(cls.length_scale)
                ),
            ),
            eps=HeteroscedasticNoise(
                cls.eps_heteroscedastic_train_n,
                _backend_fn=heteroscedastic_perturb_t,
            ),
            _backend_mean_fn=muygps_posterior_mean_t,
            _backend_var_fn=muygps_diagonal_variance_t,
            _backend_fast_mean_fn=muygps_fast_posterior_mean_t,
            _backend_fast_precompute_fn=muygps_fast_posterior_mean_precompute_t,
            _backend_math=torch,
        )
        cls.batch_indices_n, cls.batch_nn_indices_n = sample_batch(
            cls.nbrs_lookup, cls.batch_count, cls.train_count
        )
        cls.batch_indices_t = torch.from_numpy(cls.batch_indices_n)
        cls.batch_nn_indices_t = torch.from_numpy(cls.batch_nn_indices_n)


class TensorsTest(TensorsTestCase):
    @classmethod
    def setUpClass(cls):
        super(TensorsTest, cls).setUpClass()

    def test_pairwise_tensor(self):
        self.assertTrue(
            np.allclose(
                pairwise_tensor_n(
                    self.train_features_n, self.batch_nn_indices_n
                ),
                pairwise_tensor_t(
                    self.train_features_t, self.batch_nn_indices_t
                ),
            )
        )

    def test_crosswise_tensor(self):
        self.assertTrue(
            np.allclose(
                crosswise_tensor_n(
                    self.train_features_n,
                    self.train_features_n,
                    self.batch_indices_n,
                    self.batch_nn_indices_n,
                ),
                crosswise_tensor_t(
                    self.train_features_t,
                    self.train_features_t,
                    self.batch_indices_t,
                    self.batch_nn_indices_t,
                ),
            )
        )

    def test_make_train_tensors(self):
        (
            crosswise_diffs_n,
            pairwise_diffs_n,
            batch_targets_n,
            batch_nn_targets_n,
        ) = make_train_tensors_n(
            self.batch_indices_n,
            self.batch_nn_indices_n,
            self.train_features_n,
            self.train_responses_n,
        )
        (
            crosswise_diffs_t,
            pairwise_diffs_t,
            batch_targets_t,
            batch_nn_targets_t,
        ) = make_train_tensors_t(
            self.batch_indices_t,
            self.batch_nn_indices_t,
            self.train_features_t,
            self.train_responses_t,
        )
        self.assertTrue(np.allclose(crosswise_diffs_n, crosswise_diffs_t))
        self.assertTrue(np.allclose(pairwise_diffs_n, pairwise_diffs_t))
        self.assertTrue(np.allclose(batch_targets_n, batch_targets_t))
        self.assertTrue(np.allclose(batch_nn_targets_n, batch_nn_targets_t))


class KernelTestCase(TensorsTestCase):
    @classmethod
    def setUpClass(cls):
        super(KernelTestCase, cls).setUpClass()
        (
            cls.crosswise_diffs_n,
            cls.pairwise_diffs_n,
            cls.batch_targets_n,
            cls.batch_nn_targets_n,
        ) = make_train_tensors_n(
            cls.batch_indices_n,
            cls.batch_nn_indices_n,
            cls.train_features_n,
            cls.train_responses_n,
        )
        (
            cls.crosswise_diffs_t,
            cls.pairwise_diffs_t,
            cls.batch_targets_t,
            cls.batch_nn_targets_t,
        ) = make_train_tensors_t(
            cls.batch_indices_t,
            cls.batch_nn_indices_t,
            cls.train_features_t,
            cls.train_responses_t,
        )


class KernelTest(KernelTestCase):
    @classmethod
    def setUpClass(cls):
        super(KernelTest, cls).setUpClass()

    def test_crosswise_rbf(self):
        self.assertTrue(
            np.allclose(
                rbf_fn_n(
                    self.crosswise_diffs_n, length_scale=self.length_scale
                ),
                rbf_fn_t(
                    self.crosswise_diffs_t, length_scale=self.length_scale
                ),
            )
        )

    def test_pairwise_rbf(self):
        self.assertTrue(
            np.allclose(
                rbf_fn_n(self.pairwise_diffs_n, length_scale=self.length_scale),
                rbf_fn_t(self.pairwise_diffs_t, length_scale=self.length_scale),
            )
        )

    def test_crosswise_matern(self):
        self.assertTrue(
            np.allclose(
                matern_05_isotropic_fn_n(
                    self.crosswise_diffs_n, length_scale=self.length_scale
                ),
                matern_05_isotropic_fn_t(
                    self.crosswise_diffs_t, length_scale=self.length_scale
                ),
            )
        )
        self.assertTrue(
            np.allclose(
                matern_05_anisotropic_fn_n(
                    self.crosswise_diffs_n, length_scale0=self.length_scale
                ),
                matern_05_anisotropic_fn_t(
                    self.crosswise_diffs_t, length_scale0=self.length_scale
                ),
            )
        )
        self.assertTrue(
            np.allclose(
                matern_15_isotropic_fn_n(
                    self.crosswise_diffs_n, length_scale=self.length_scale
                ),
                matern_15_isotropic_fn_t(
                    self.crosswise_diffs_t, length_scale=self.length_scale
                ),
            )
        )
        self.assertTrue(
            np.allclose(
                matern_15_anisotropic_fn_n(
                    self.crosswise_diffs_n, length_scale0=self.length_scale
                ),
                matern_15_anisotropic_fn_t(
                    self.crosswise_diffs_t, length_scale0=self.length_scale
                ),
            )
        )
        self.assertTrue(
            np.allclose(
                matern_25_isotropic_fn_n(
                    self.crosswise_diffs_n, length_scale=self.length_scale
                ),
                matern_25_isotropic_fn_t(
                    self.crosswise_diffs_t, length_scale=self.length_scale
                ),
            )
        )
        self.assertTrue(
            np.allclose(
                matern_25_anisotropic_fn_n(
                    self.crosswise_diffs_n, length_scale0=self.length_scale
                ),
                matern_25_anisotropic_fn_t(
                    self.crosswise_diffs_t, length_scale0=self.length_scale
                ),
            )
        )
        self.assertTrue(
            np.allclose(
                matern_inf_isotropic_fn_n(
                    self.crosswise_diffs_n, length_scale=self.length_scale
                ),
                matern_inf_isotropic_fn_t(
                    self.crosswise_diffs_t, length_scale=self.length_scale
                ),
            )
        )
        self.assertTrue(
            np.allclose(
                matern_inf_anisotropic_fn_n(
                    self.crosswise_diffs_n, length_scale0=self.length_scale
                ),
                matern_inf_anisotropic_fn_t(
                    self.crosswise_diffs_t, length_scale0=self.length_scale
                ),
            )
        )

    def test_pairwise_matern(self):
        self.assertTrue(
            np.allclose(
                matern_05_isotropic_fn_n(
                    self.pairwise_diffs_n, length_scale=self.length_scale
                ),
                matern_05_isotropic_fn_t(
                    self.pairwise_diffs_t, length_scale=self.length_scale
                ),
            )
        )
        self.assertTrue(
            np.allclose(
                matern_05_anisotropic_fn_n(
                    self.pairwise_diffs_n, length_scale0=self.length_scale
                ),
                matern_05_anisotropic_fn_t(
                    self.pairwise_diffs_t, length_scale0=self.length_scale
                ),
            )
        )
        self.assertTrue(
            np.allclose(
                matern_15_isotropic_fn_n(
                    self.pairwise_diffs_n, length_scale=self.length_scale
                ),
                matern_15_isotropic_fn_t(
                    self.pairwise_diffs_t, length_scale=self.length_scale
                ),
            )
        )
        self.assertTrue(
            np.allclose(
                matern_15_anisotropic_fn_n(
                    self.pairwise_diffs_n, length_scale0=self.length_scale
                ),
                matern_15_anisotropic_fn_t(
                    self.pairwise_diffs_t, length_scale0=self.length_scale
                ),
            )
        )
        self.assertTrue(
            np.allclose(
                matern_25_isotropic_fn_n(
                    self.pairwise_diffs_n, length_scale=self.length_scale
                ),
                matern_25_isotropic_fn_t(
                    self.pairwise_diffs_t, length_scale=self.length_scale
                ),
            )
        )
        self.assertTrue(
            np.allclose(
                matern_25_anisotropic_fn_n(
                    self.pairwise_diffs_n, length_scale0=self.length_scale
                ),
                matern_25_anisotropic_fn_t(
                    self.pairwise_diffs_t, length_scale0=self.length_scale
                ),
            )
        )
        self.assertTrue(
            np.allclose(
                matern_inf_isotropic_fn_n(
                    self.pairwise_diffs_n, length_scale=self.length_scale
                ),
                matern_inf_isotropic_fn_t(
                    self.pairwise_diffs_t, length_scale=self.length_scale
                ),
            )
        )
        self.assertTrue(
            np.allclose(
                matern_inf_anisotropic_fn_n(
                    self.pairwise_diffs_n, length_scale0=self.length_scale
                ),
                matern_inf_anisotropic_fn_t(
                    self.pairwise_diffs_t, length_scale0=self.length_scale
                ),
            )
        )


class MuyGPSTestCase(KernelTestCase):
    @classmethod
    def setUpClass(cls):
        super(MuyGPSTestCase, cls).setUpClass()
        cls.K_n = matern_05_isotropic_fn_n(
            cls.pairwise_diffs_n, length_scale=cls.length_scale
        )
        cls.K_t = matern_05_isotropic_fn_t(
            cls.pairwise_diffs_t, length_scale=cls.length_scale
        )
        cls.homoscedastic_K_n = cls.muygps_n.eps.perturb(cls.K_n)

        cls.heteroscedastic_K_n = cls.muygps_heteroscedastic_n.eps.perturb(
            cls.K_n,
        )

        cls.homoscedastic_K_t = cls.muygps_t.eps.perturb(cls.K_t)
        cls.heteroscedastic_K_t = cls.muygps_heteroscedastic_t.eps.perturb(
            cls.K_t
        )

        cls.Kcross_n = matern_05_isotropic_fn_n(
            cls.crosswise_diffs_n, length_scale=cls.length_scale
        )
        cls.Kcross_t = matern_05_isotropic_fn_t(
            cls.crosswise_diffs_t, length_scale=cls.length_scale
        )


class MuyGPSTest(MuyGPSTestCase):
    @classmethod
    def setUpClass(cls):
        super(MuyGPSTest, cls).setUpClass()

    def test_homoscedastic_noise(self):
        self.assertTrue(
            np.allclose(self.homoscedastic_K_n, self.homoscedastic_K_t)
        )

    def test_heteroscedastic_noise(self):
        self.assertTrue(
            np.allclose(self.heteroscedastic_K_n, self.heteroscedastic_K_t)
        )

    def test_posterior_mean(self):
        self.assertTrue(
            _allclose(
                muygps_posterior_mean_n(
                    self.homoscedastic_K_n,
                    self.Kcross_n,
                    self.batch_nn_targets_n,
                ),
                muygps_posterior_mean_t(
                    self.homoscedastic_K_t,
                    self.Kcross_t,
                    self.batch_nn_targets_t,
                ),
            )
        )

    def test_posterior_mean_heteroscedastic(self):
        self.assertTrue(
            _allclose(
                muygps_posterior_mean_n(
                    self.heteroscedastic_K_n,
                    self.Kcross_n,
                    self.batch_nn_targets_n,
                ),
                muygps_posterior_mean_t(
                    self.heteroscedastic_K_t,
                    self.Kcross_t,
                    self.batch_nn_targets_t,
                ),
            )
        )

    def test_diagonal_variance(self):
        self.assertTrue(
            np.allclose(
                muygps_diagonal_variance_n(
                    self.homoscedastic_K_n, self.Kcross_n
                ),
                muygps_diagonal_variance_t(
                    self.homoscedastic_K_t, self.Kcross_t
                ),
            )
        )

    def test_diagonal_variance_heteroscedastic(self):
        self.assertTrue(
            np.allclose(
                muygps_diagonal_variance_n(
                    self.heteroscedastic_K_n, self.Kcross_n
                ),
                muygps_diagonal_variance_t(
                    self.heteroscedastic_K_t, self.Kcross_t
                ),
            )
        )

    def test_sigma_sq_optim(self):
        self.assertTrue(
            np.allclose(
                analytic_sigma_sq_optim_n(
                    self.homoscedastic_K_n, self.batch_nn_targets_n
                ),
                analytic_sigma_sq_optim_t(
                    self.homoscedastic_K_t, self.batch_nn_targets_t
                ),
            )
        )

    def test_sigma_sq_optim_heteroscedastic(self):
        self.assertTrue(
            np.allclose(
                analytic_sigma_sq_optim_n(
                    self.heteroscedastic_K_n, self.batch_nn_targets_n
                ),
                analytic_sigma_sq_optim_t(
                    self.heteroscedastic_K_t, self.batch_nn_targets_t
                ),
            )
        )


class FastPredictTest(MuyGPSTestCase):
    @classmethod
    def setUpClass(cls):
        super(FastPredictTest, cls).setUpClass()
        cls.nn_indices_all_n, _ = cls.nbrs_lookup.get_batch_nns(
            np.arange(0, cls.train_count)
        )
        (
            cls.K_fast_n,
            cls.train_nn_targets_fast_n,
        ) = make_fast_predict_tensors_n(
            cls.nn_indices_all_n,
            cls.train_features_n,
            cls.train_responses_n,
        )

        cls.homoscedastic_K_fast_n = cls.muygps_n.eps.perturb(
            l2_n(cls.K_fast_n)
        )
        cls.heteroscedastic_K_fast_n = (
            cls.muygps_heteroscedastic_train_n.eps.perturb(l2_n(cls.K_fast_n))
        )
        cls.fast_regress_coeffs_n = muygps_fast_posterior_mean_precompute_n(
            cls.homoscedastic_K_fast_n, cls.train_nn_targets_fast_n
        )
        cls.fast_regress_coeffs_heteroscedastic_n = (
            muygps_fast_posterior_mean_precompute_n(
                cls.heteroscedastic_K_fast_n, cls.train_nn_targets_fast_n
            )
        )

        cls.test_neighbors_n, _ = cls.nbrs_lookup.get_nns(cls.test_features_n)
        cls.closest_neighbor_n = cls.test_neighbors_n[:, 0]
        cls.closest_set_n = cls.nn_indices_all_n[cls.closest_neighbor_n]

        cls.new_nn_indices_n = fast_nn_update_n(cls.nn_indices_all_n)
        cls.closest_set_new_n = cls.new_nn_indices_n[
            cls.closest_neighbor_n
        ].astype(int)
        cls.crosswise_diffs_fast_n = crosswise_tensor_n(
            cls.test_features_n,
            cls.train_features_n,
            np.arange(0, cls.test_count),
            cls.closest_set_new_n,
        )

        kernel_func_n = matern_05_isotropic_fn_n
        cls.Kcross_fast_n = kernel_func_n(cls.crosswise_diffs_fast_n)

        cls.nn_indices_all_t, _ = cls.nbrs_lookup.get_batch_nns(
            torch.arange(0, cls.train_count)
        )
        cls.nn_indices_all_t = torch.from_numpy(cls.nn_indices_all_t)
        (
            cls.K_fast_t,
            cls.train_nn_targets_fast_t,
        ) = make_fast_predict_tensors_t(
            cls.nn_indices_all_t,
            cls.train_features_t,
            cls.train_responses_t,
        )

        cls.homoscedastic_K_fast_t = cls.muygps_t.eps.perturb(
            l2_t(cls.K_fast_t)
        )
        cls.heteroscedastic_K_fast_t = (
            cls.muygps_heteroscedastic_train_t.eps.perturb(l2_t(cls.K_fast_t))
        )
        cls.fast_regress_coeffs_t = muygps_fast_posterior_mean_precompute_t(
            cls.homoscedastic_K_fast_t, cls.train_nn_targets_fast_t
        )
        cls.fast_regress_coeffs_heteroscedastic_t = (
            muygps_fast_posterior_mean_precompute_t(
                cls.heteroscedastic_K_fast_t, cls.train_nn_targets_fast_t
            )
        )

        cls.test_neighbors_t, _ = cls.nbrs_lookup.get_nns(cls.test_features_t)
        cls.closest_neighbor_t = cls.test_neighbors_t[:, 0]
        cls.closest_set_t = cls.nn_indices_all_t[cls.closest_neighbor_t]

        cls.new_nn_indices_t = fast_nn_update_t(cls.nn_indices_all_t)
        cls.closest_set_new_t = cls.new_nn_indices_t[cls.closest_neighbor_t]
        cls.crosswise_diffs_fast_t = crosswise_tensor_t(
            cls.test_features_t,
            cls.train_features_t,
            torch.arange(0, cls.test_count),
            cls.closest_set_new_t,
        )

        kernel_func_t = matern_05_isotropic_fn_t
        cls.Kcross_fast_t = kernel_func_t(cls.crosswise_diffs_fast_t)

    def test_fast_nn_update(self):
        self.assertTrue(
            np.allclose(
                fast_nn_update_t(self.nn_indices_all_t),
                fast_nn_update_n(self.nn_indices_all_n),
            )
        )

    def test_make_fast_predict_tensors(self):
        self.assertTrue(np.allclose(self.K_fast_n, self.K_fast_t))
        self.assertTrue(
            np.allclose(
                self.train_nn_targets_fast_n, self.train_nn_targets_fast_t
            )
        )

    def test_homoscedastic_kernel_tensors(self):
        self.assertTrue(
            np.allclose(
                self.homoscedastic_K_fast_n, self.homoscedastic_K_fast_t
            )
        )

    def test_heteroscedastic_kernel_tensors(self):
        self.assertTrue(
            np.allclose(
                self.heteroscedastic_K_fast_n, self.heteroscedastic_K_fast_t
            )
        )

    def test_fast_predict(self):
        self.assertTrue(
            _allclose(
                muygps_fast_posterior_mean_n(
                    self.Kcross_fast_n,
                    self.fast_regress_coeffs_n[self.closest_neighbor_n, :],
                ),
                muygps_fast_posterior_mean_t(
                    self.Kcross_fast_t,
                    self.fast_regress_coeffs_t[self.closest_neighbor_t, :],
                ),
            )
        )

    def test_fast_predict_heteroscedastic(self):
        self.assertTrue(
            _allclose(
                muygps_fast_posterior_mean_n(
                    self.Kcross_fast_n,
                    self.fast_regress_coeffs_heteroscedastic_n[
                        self.closest_neighbor_n, :
                    ],
                ),
                muygps_fast_posterior_mean_t(
                    self.Kcross_fast_t,
                    self.fast_regress_coeffs_heteroscedastic_t[
                        self.closest_neighbor_t, :
                    ],
                ),
            )
        )

    def test_fast_predict_coeffs(self):
        self.assertTrue(
            _allclose(
                self.fast_regress_coeffs_n,
                self.fast_regress_coeffs_t,
            )
        )


class FastMultivariatePredictTest(MuyGPSTestCase):
    @classmethod
    def setUpClass(cls):
        super(FastMultivariatePredictTest, cls).setUpClass()
        cls.train_count = 1000
        cls.test_count = 100
        cls.feature_count = 10
        cls.response_count = 2
        cls.nn_count = 40
        cls.batch_count = 500
        cls.length_scale = 1.0
        cls.nu = 0.5
        cls.nu_bounds = (1e-1, 1e1)
        cls.eps = 1e-3
        cls.eps_heteroscedastic_n = _make_heteroscedastic_test_nugget(
            cls.batch_count, cls.nn_count, cls.eps
        )
        cls.eps_heteroscedastic_train_n = _make_heteroscedastic_test_nugget(
            cls.train_count, cls.nn_count, cls.eps
        )
        cls.eps_heteroscedastic_t = torch.ndarray(cls.eps_heteroscedastic_n)
        cls.eps_heteroscedastic_train_t = torch.ndarray(
            cls.eps_heteroscedastic_train_n
        )
        cls.k_kwargs_n = [
            {
                "kernel": Matern(
                    nu=ScalarHyperparameter(cls.nu, cls.nu_bounds),
                    metric=IsotropicDistortion(
                        l2_n,
                        length_scale=ScalarHyperparameter(cls.length_scale),
                    ),
                ),
                "eps": HeteroscedasticNoise(
                    cls.eps_heteroscedastic_train_n,
                    _backend_fn=heteroscedastic_perturb_n,
                ),
            },
            {
                "kernel": Matern(
                    nu=ScalarHyperparameter(cls.nu, cls.nu_bounds),
                    metric=IsotropicDistortion(
                        l2_n,
                        length_scale=ScalarHyperparameter(cls.length_scale),
                    ),
                ),
                "eps": HeteroscedasticNoise(
                    cls.eps_heteroscedastic_train_n,
                    _backend_fn=heteroscedastic_perturb_n,
                ),
            },
        ]
        cls.train_features_n = _make_gaussian_matrix(
            cls.train_count, cls.feature_count
        )
        cls.train_features_t = torch.from_numpy(cls.train_features_n)
        cls.train_responses_n = _make_gaussian_matrix(
            cls.train_count, cls.response_count
        )
        cls.train_responses_t = torch.from_numpy(cls.train_responses_n)
        cls.test_features_n = _make_gaussian_matrix(
            cls.test_count, cls.feature_count
        )
        cls.test_features_t = torch.from_numpy(cls.test_features_n)
        cls.test_responses_n = _make_gaussian_matrix(
            cls.test_count, cls.response_count
        )
        cls.test_responses_t = torch.from_numpy(cls.test_responses_n)
        cls.nbrs_lookup = NN_Wrapper(
            cls.train_features_n, cls.nn_count, **_exact_nn_kwarg_options[0]
        )
        cls.mmuygps_n = MMuyGPS(*cls.k_kwargs_n)
        cls.batch_indices_n, cls.batch_nn_indices_n = sample_batch(
            cls.nbrs_lookup, cls.batch_count, cls.train_count
        )
        cls.batch_indices_t = torch.from_numpy(cls.batch_indices_n)
        cls.batch_nn_indices_t = torch.from_numpy(cls.batch_nn_indices_n)
        cls.nn_indices_all_n, _ = cls.nbrs_lookup.get_batch_nns(
            np.arange(0, cls.train_count)
        )
        (
            cls.K_fast_n,
            cls.train_nn_targets_fast_n,
        ) = make_fast_predict_tensors_n(
            cls.nn_indices_all_n,
            cls.train_features_n,
            cls.train_responses_n,
        )

        cls.homoscedastic_K_fast_n = homoscedastic_perturb_n(
            l2_n(cls.K_fast_n), cls.eps
        )
        cls.heteroscedastic_K_fast_n = heteroscedastic_perturb_n(
            l2_n(cls.K_fast_n), cls.eps_heteroscedastic_train_n
        )

        cls.fast_regress_coeffs_n = muygps_fast_posterior_mean_precompute_n(
            cls.homoscedastic_K_fast_n, cls.train_nn_targets_fast_n
        )

        cls.test_neighbors_n, _ = cls.nbrs_lookup.get_nns(cls.test_features_n)
        cls.closest_neighbor_n = cls.test_neighbors_n[:, 0]
        cls.closest_set_n = cls.nn_indices_all_n[cls.closest_neighbor_n]

        cls.new_nn_indices_n = fast_nn_update_n(cls.nn_indices_all_n)
        cls.closest_set_new_n = cls.new_nn_indices_n[
            cls.closest_neighbor_n
        ].astype(int)
        cls.crosswise_diffs_fast_n = crosswise_tensor_n(
            cls.test_features_n,
            cls.train_features_n,
            np.arange(0, cls.test_count),
            cls.closest_set_new_n,
        )
        Kcross_fast_n = np.zeros(
            (cls.test_count, cls.nn_count, cls.response_count)
        )
        kernel_func_n = matern_05_isotropic_fn_n
        for i, model in enumerate(cls.mmuygps_n.models):
            Kcross_fast_n[:, :, i] = kernel_func_n(cls.crosswise_diffs_fast_n)
        cls.Kcross_fast_n = Kcross_fast_n

        cls.nn_indices_all_t, _ = cls.nbrs_lookup.get_batch_nns(
            torch.arange(0, cls.train_count)
        )
        cls.nn_indices_all_t = torch.from_numpy(cls.nn_indices_all_n)

        (
            cls.K_fast_t,
            cls.train_nn_targets_fast_t,
        ) = make_fast_predict_tensors_t(
            cls.nn_indices_all_t,
            cls.train_features_t,
            cls.train_responses_t,
        )

        cls.homoscedastic_K_fast_t = homoscedastic_perturb_t(
            l2_t(cls.K_fast_t), cls.eps
        )

        cls.heteroscedastic_K_fast_t = heteroscedastic_perturb_t(
            l2_t(cls.K_fast_t), cls.eps_heteroscedastic_train_t
        )

        cls.fast_regress_coeffs_t = muygps_fast_posterior_mean_precompute_t(
            cls.homoscedastic_K_fast_t, cls.train_nn_targets_fast_t
        )

        cls.fast_regress_coeffs_heteroscedastic_t = (
            muygps_fast_posterior_mean_precompute_t(
                cls.heteroscedastic_K_fast_t, cls.train_nn_targets_fast_t
            )
        )

        cls.test_neighbors_t, _ = cls.nbrs_lookup.get_nns(cls.test_features_t)
        cls.closest_neighbor_t = cls.test_neighbors_t[:, 0]
        cls.closest_set_t = cls.nn_indices_all_t[cls.closest_neighbor_t]

        cls.new_nn_indices_t = fast_nn_update_t(cls.nn_indices_all_t)
        cls.closest_set_new_t = cls.new_nn_indices_t[cls.closest_neighbor_t]
        cls.crosswise_diffs_fast_t = crosswise_tensor_t(
            cls.test_features_t,
            cls.train_features_t,
            torch.arange(0, cls.test_count),
            cls.closest_set_new_t,
        )

        cls.Kcross_fast_t = torch.from_numpy(Kcross_fast_n)

    def test_make_fast_multivariate_predict_tensors(self):
        self.assertTrue(np.allclose(self.K_fast_n, self.K_fast_t))
        self.assertTrue(
            np.allclose(
                self.train_nn_targets_fast_n, self.train_nn_targets_fast_t
            )
        )

    def test_fast_multivariate_predict(self):
        self.assertTrue(
            _allclose(
                mmuygps_fast_posterior_mean_n(
                    self.Kcross_fast_n,
                    self.fast_regress_coeffs_n[self.closest_neighbor_n, :],
                ),
                mmuygps_fast_posterior_mean_t(
                    self.Kcross_fast_t,
                    self.fast_regress_coeffs_t[self.closest_neighbor_t, :],
                ),
            )
        )

    def test_fast_multivariate_predict_coeffs(self):
        self.assertTrue(
            _allclose(
                self.fast_regress_coeffs_n,
                self.fast_regress_coeffs_t,
            )
        )


class OptimTestCase(MuyGPSTestCase):
    @classmethod
    def setUpClass(cls):
        super(OptimTestCase, cls).setUpClass()
        cls.predictions_t = muygps_posterior_mean_t(
            cls.homoscedastic_K_t, cls.Kcross_t, cls.batch_nn_targets_t
        )
        cls.variances_t = muygps_diagonal_variance_t(
            cls.homoscedastic_K_t, cls.Kcross_t
        )
        cls.predictions_heteroscedastic_t = muygps_posterior_mean_t(
            cls.heteroscedastic_K_t, cls.Kcross_t, cls.batch_nn_targets_t
        )
        cls.variances_heteroscedastic_t = muygps_diagonal_variance_t(
            cls.heteroscedastic_K_t, cls.Kcross_t
        )
        cls.predictions_n = cls.predictions_t.detach().numpy()
        cls.variances_n = cls.variances_t.detach().numpy()
        cls.x0_names, cls.x0_n, cls.bounds = cls.muygps_n.get_opt_params()
        cls.x0_t = torch.from_numpy(cls.x0_n)
        cls.x0_map_n = {n: cls.x0_n[i] for i, n in enumerate(cls.x0_names)}
        cls.x0_map_t = {n: cls.x0_t[i] for i, n in enumerate(cls.x0_names)}

    def _get_kernel_fn_n(self):
        return self.muygps_n.kernel._get_opt_fn(
            matern_05_isotropic_fn_n,
            IsotropicDistortion(
                l2_n, length_scale=ScalarHyperparameter(self.length_scale)
            ),
            nu=self.muygps_n.kernel.nu,
        )

    def _get_kernel_fn_t(self):
        return self.muygps_t.kernel._get_opt_fn(
            matern_05_isotropic_fn_t,
            IsotropicDistortion(
                l2_t, length_scale=ScalarHyperparameter(self.length_scale)
            ),
            nu=self.muygps_t.kernel.nu,
        )

    def _get_sigma_sq_fn_n(self):
        return make_analytic_sigma_sq_optim(
            self.muygps_n, analytic_sigma_sq_optim_n
        )

    def _get_sigma_sq_fn_heteroscedastic_n(self):
        return make_analytic_sigma_sq_optim(
            self.muygps_heteroscedastic_n, analytic_sigma_sq_optim_n
        )

    def _get_sigma_sq_fn_t(self):
        return make_analytic_sigma_sq_optim(
            self.muygps_t, analytic_sigma_sq_optim_t
        )

    def _get_sigma_sq_fn_heteroscedastic_t(self):
        return make_analytic_sigma_sq_optim(
            self.muygps_heteroscedastic_t, analytic_sigma_sq_optim_t
        )

    def _get_obj_fn_n(self):
        return make_loo_crossval_fn(
            mse_fn_n,
            self._get_kernel_fn_n(),
            self.muygps_n.get_opt_mean_fn(),
            self.muygps_n.get_opt_var_fn(),
            self._get_sigma_sq_fn_n(),
            self.pairwise_diffs_n,
            self.crosswise_diffs_n,
            self.batch_nn_targets_n,
            self.batch_targets_n,
        )

    def _get_obj_fn_heteroscedastic_n(self):
        return make_loo_crossval_fn(
            mse_fn_n,
            self._get_kernel_fn_n(),
            self.muygps_heteroscedastic_n.get_opt_mean_fn(),
            self.muygps_heteroscedastic_n.get_opt_var_fn(),
            self._get_sigma_sq_fn_heteroscedastic_n(),
            self.pairwise_diffs_n,
            self.crosswise_diffs_n,
            self.batch_nn_targets_n,
            self.batch_targets_n,
        )

    def _get_obj_fn_t(self):
        return make_loo_crossval_fn(
            mse_fn_t,
            self._get_kernel_fn_t(),
            self.muygps_t.get_opt_mean_fn(),
            self.muygps_t.get_opt_var_fn(),
            self._get_sigma_sq_fn_t(),
            self.pairwise_diffs_t,
            self.crosswise_diffs_t,
            self.batch_nn_targets_t,
            self.batch_targets_t,
        )

    def _get_obj_fn_heteroscedastic_t(self):
        return make_loo_crossval_fn(
            mse_fn_t,
            self._get_kernel_fn_t(),
            self.muygps_heteroscedastic_t.get_opt_mean_fn(),
            self.muygps_heteroscedastic_t.get_opt_var_fn(),
            self._get_sigma_sq_fn_heteroscedastic_t(),
            self.pairwise_diffs_t,
            self.crosswise_diffs_t,
            self.batch_nn_targets_t,
            self.batch_targets_t,
        )


class ObjectiveTest(OptimTestCase):
    @classmethod
    def setUpClass(cls):
        super(ObjectiveTest, cls).setUpClass()

        cls.sigma_sq_n = cls.muygps_n.sigma_sq()
        cls.sigma_sq_t = torch.array(cls.muygps_t.sigma_sq()).float()

    def test_mse(self):
        self.assertTrue(
            np.isclose(
                mse_fn_n(self.predictions_n, self.batch_targets_n),
                mse_fn_t(self.predictions_t, self.batch_targets_t),
            )
        )

    def test_lool(self):
        self.assertTrue(
            np.isclose(
                lool_fn_n(
                    self.predictions_n,
                    self.batch_targets_n,
                    self.variances_n,
                    self.sigma_sq_n,
                ),
                lool_fn_t(
                    self.predictions_t,
                    self.batch_targets_t,
                    self.variances_t,
                    self.sigma_sq_t,
                ),
            )
        )

    @parameterized.parameters(bs for bs in [0.5, 1.0, 1.5, 2.0, 2.5])
    def test_pseudo_huber(self, boundary_scale):
        self.assertTrue(
            np.isclose(
                pseudo_huber_fn_n(
                    self.predictions_n, self.batch_targets_n, boundary_scale
                ),
                pseudo_huber_fn_t(
                    self.predictions_t, self.batch_targets_t, boundary_scale
                ),
            )
        )

    @parameterized.parameters(bs for bs in [0.5, 1.0, 1.5, 2.0, 2.5])
    def test_looph(self, boundary_scale):
        self.assertTrue(
            np.isclose(
                looph_fn_n(
                    self.predictions_n,
                    self.batch_targets_n,
                    self.variances_n,
                    self.sigma_sq_n,
                    boundary_scale=boundary_scale,
                ),
                looph_fn_t(
                    self.predictions_t,
                    self.batch_targets_t,
                    self.variances_t,
                    self.sigma_sq_t,
                    boundary_scale=boundary_scale,
                ),
            )
        )

    def test_cross_entropy(self):
        cat_predictions_n, cat_batch_targets_n = _make_gaussian_data(
            1000, 1000, 10, 2, categorical=True
        )
        cat_predictions_n = cat_predictions_n["output"]
        cat_batch_targets_n = cat_batch_targets_n["output"]
        cat_predictions_t = torch.from_numpy(cat_predictions_n)
        cat_batch_targets_t = torch.from_numpy(cat_batch_targets_n)
        self.assertTrue(
            np.all(
                (
                    np.allclose(cat_predictions_t, cat_predictions_n),
                    np.allclose(cat_batch_targets_t, cat_batch_targets_n),
                )
            )
        )
        self.assertTrue(
            np.allclose(
                cross_entropy_fn_n(
                    cat_predictions_n, cat_batch_targets_n, ll_eps=1e-6
                ),
                cross_entropy_fn_t(cat_predictions_t, cat_batch_targets_t),
            )
        )

    def test_kernel_fn(self):
        kernel_fn_n = self._get_kernel_fn_n()
        kernel_fn_t = self._get_kernel_fn_t()
        self.assertTrue(
            np.allclose(
                kernel_fn_n(self.pairwise_diffs_n, **self.x0_map_n),
                kernel_fn_t(self.pairwise_diffs_t, **self.x0_map_t),
            )
        )

    def test_mean_fn(self):
        mean_fn_n = self.muygps_n.get_opt_mean_fn()
        mean_fn_t = self.muygps_t.get_opt_mean_fn()
        self.assertTrue(
            _allclose(
                mean_fn_n(
                    self.K_n,
                    self.Kcross_n,
                    self.batch_nn_targets_n,
                    **self.x0_map_n,
                ),
                mean_fn_t(
                    self.K_t,
                    self.Kcross_t,
                    self.batch_nn_targets_t,
                    **self.x0_map_t,
                ),
            )
        )

    def test_mean_heteroscedastic_fn(self):
        mean_fn_n = self.muygps_heteroscedastic_n.get_opt_mean_fn()
        mean_fn_t = self.muygps_heteroscedastic_t.get_opt_mean_fn()
        self.assertTrue(
            _allclose(
                mean_fn_n(
                    self.K_n,
                    self.Kcross_n,
                    self.batch_nn_targets_n,
                    **self.x0_map_n,
                ),
                mean_fn_t(
                    self.K_t,
                    self.Kcross_t,
                    self.batch_nn_targets_t,
                    **self.x0_map_t,
                ),
            )
        )

    def test_var_fn(self):
        var_fn_n = self.muygps_n.get_opt_var_fn()
        var_fn_t = self.muygps_t.get_opt_var_fn()
        self.assertTrue(
            np.allclose(
                var_fn_n(
                    self.K_n,
                    self.Kcross_n,
                    **self.x0_map_n,
                ),
                var_fn_t(
                    self.K_t,
                    self.Kcross_t,
                    **self.x0_map_t,
                ),
            )
        )

    def test_var_heteroscedastic_fn(self):
        var_fn_n = self.muygps_heteroscedastic_n.get_opt_var_fn()
        var_fn_t = self.muygps_heteroscedastic_t.get_opt_var_fn()
        self.assertTrue(
            np.allclose(
                var_fn_n(
                    self.K_n,
                    self.Kcross_n,
                    **self.x0_map_n,
                ),
                var_fn_t(
                    self.K_t,
                    self.Kcross_t,
                    **self.x0_map_t,
                ),
            )
        )

    def test_sigma_sq_fn(self):
        ss_fn_n = self._get_sigma_sq_fn_n()
        ss_fn_t = self._get_sigma_sq_fn_t()
        self.assertTrue(
            np.allclose(
                ss_fn_n(
                    self.K_n,
                    self.batch_nn_targets_n,
                    **self.x0_map_n,
                ),
                ss_fn_t(
                    self.K_t,
                    self.batch_nn_targets_t,
                    **self.x0_map_t,
                ),
            )
        )

    def test_sigma_sq_heteroscedastic_fn(self):
        ss_fn_n = self._get_sigma_sq_fn_heteroscedastic_n()
        ss_fn_t = self._get_sigma_sq_fn_heteroscedastic_t()
        self.assertTrue(
            np.allclose(
                ss_fn_n(
                    self.K_n,
                    self.batch_nn_targets_n,
                    **self.x0_map_n,
                ),
                ss_fn_t(
                    self.K_t,
                    self.batch_nn_targets_t,
                    **self.x0_map_t,
                ),
            )
        )

    def test_loo_crossval(self):
        obj_fn_n = self._get_obj_fn_n()
        obj_fn_t = self._get_obj_fn_t()
        self.assertTrue(
            np.allclose(obj_fn_n(**self.x0_map_n), obj_fn_t(**self.x0_map_t))
        )

    def test_loo_crossval_heteroscedastic(self):
        obj_fn_n = self._get_obj_fn_heteroscedastic_n()
        obj_fn_t = self._get_obj_fn_heteroscedastic_t()
        self.assertTrue(
            np.allclose(obj_fn_n(**self.x0_map_n), obj_fn_t(**self.x0_map_t))
        )


if __name__ == "__main__":
    absltest.main()
