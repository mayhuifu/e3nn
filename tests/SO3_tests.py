# pylint: disable=not-callable, no-member, invalid-name, line-too-long, wildcard-import, unused-wildcard-import, missing-docstring
import unittest

import torch

from se3cnn.SO3 import *


class Tests(unittest.TestCase):

    def test_sh_norm(self):
        with torch_default_dtype(torch.float64):
            l_filter = list(range(15))
            Ys = [spherical_harmonics_xyz(l, torch.randn(10, 3)) for l in l_filter]
            s = torch.stack([Y.pow(2).mean(0).mean() for Y in Ys])
            d = s - 1 / (4 * math.pi)
            assert d.pow(2).mean().sqrt() < 1e-10


    def test_clebsch_gordan_orthogonal(self):
        with torch_default_dtype(torch.float64):
            for l_out in range(6):
                for l_in in range(6):
                    for l_f in range(abs(l_out - l_in), l_out + l_in + 1):
                        Q = clebsch_gordan(l_f, l_in, l_out).view(2 * l_f + 1, -1)
                        e = (2 * l_f + 1) * Q @ Q.t()
                        d = e - torch.eye(2 * l_f + 1)
                        assert d.pow(2).mean().sqrt() < 1e-10


    def test_clebsch_gordan_sh_norm(self):
        with torch_default_dtype(torch.float64):
            for l_out in range(6):
                for l_in in range(6):
                    for l_f in range(abs(l_out - l_in), l_out + l_in + 1):
                        Q = clebsch_gordan(l_out, l_in, l_f)
                        Y = spherical_harmonics_xyz(l_f, torch.randn(1, 3)).view(2 * l_f + 1)
                        QY = math.sqrt(4 * math.pi) * Q @ Y
                        assert abs(QY.norm() - 1) < 1e-10


    def test_rot_to_abc(self):
        with torch_default_dtype(torch.float64):
            R = rand_rot()
            abc = rot_to_abc(R)
            R2 = rot(*abc)
            d = (R - R2).norm() / R.norm()
            self.assertTrue(d < 1e-10, d)


    def _test_is_representation(self, rep):
        """
        rep(Z(a1) Y(b1) Z(c1) Z(a2) Y(b2) Z(c2)) = rep(Z(a1) Y(b1) Z(c1)) rep(Z(a2) Y(b2) Z(c2))
        """
        with torch_default_dtype(torch.float64):
            a1, b1, c1, a2, b2, c2 = torch.rand(6)

            r1 = rep(a1, b1, c1)
            r2 = rep(a2, b2, c2)

            a, b, c = compose(a1, b1, c1, a2, b2, c2)
            r = rep(a, b, c)

            r_ = r1 @ r2

            d, r = (r - r_).abs().max(), r.abs().max()
            print(d.item(), r.item())
            self.assertTrue(d < 1e-10 * r, d / r)


    def _test_spherical_harmonics(self, order):
        """
        This test tests that
        - irr_repr
        - compose
        - spherical_harmonics
        are compatible

        Y(Z(alpha) Y(beta) Z(gamma) x) = D(alpha, beta, gamma) Y(x)
        with x = Z(a) Y(b) eta
        """
        with torch_default_dtype(torch.float64):
            a, b = torch.rand(2)
            alpha, beta, gamma = torch.rand(3)

            ra, rb, _ = compose(alpha, beta, gamma, a, b, 0)
            Yrx = spherical_harmonics(order, ra, rb)

            Y = spherical_harmonics(order, a, b)
            DrY = irr_repr(order, alpha, beta, gamma) @ Y

            d, r = (Yrx - DrY).abs().max(), Y.abs().max()
            print(d.item(), r.item())
            self.assertTrue(d < 1e-10 * r, d / r)


    def _test_change_basis_wigner_to_rot(self, ):
        with torch_default_dtype(torch.float64):
            A = torch.tensor([
                [0, 1, 0],
                [0, 0, 1],
                [1, 0, 0]
            ], dtype=torch.float64)

            a, b, c = torch.rand(3)

            r1 = A.t() @ irr_repr(1, a, b, c) @ A
            r2 = rot(a, b, c)

            d = (r1 - r2).abs().max()
            print(d.item())
            self.assertTrue(d < 1e-10)


    def _test_reduce_tensor_product(self, Rs_i, Rs_j):
        Rs, Q = reduce_tensor_product(Rs_i, Rs_j)

        abc = torch.rand(3, dtype=torch.float64)

        D_i = direct_sum(*[irr_repr(l, *abc) for mul, l in Rs_i for _ in range(mul)])
        D_j = direct_sum(*[irr_repr(l, *abc) for mul, l in Rs_j for _ in range(mul)])
        D = direct_sum(*[irr_repr(l, *abc) for mul, l in Rs for _ in range(mul)])

        Q1 = torch.einsum("ijk,kl->ijl", (Q, D))
        Q2 = torch.einsum("li,mj,ijk->lmk", (D_i, D_j, Q))

        d = (Q1 - Q2).pow(2).mean().sqrt() / Q1.pow(2).mean().sqrt()
        print(d.item())
        self.assertLess(d, 1e-10)

        n = Q.size(2)
        M = Q.view(n, n)
        I = torch.eye(n, dtype=M.dtype)

        d = ((M @ M.t()) - I).pow(2).mean().sqrt()
        self.assertLess(d, 1e-10)

        d = ((M.t() @ M) - I).pow(2).mean().sqrt()
        self.assertLess(d, 1e-10)


    def test(self):
        from functools import partial

        print("Change of basis")
        xyz_vector_basis_to_spherical_basis()
        self._test_is_representation(tensor3x3_repr)
        tensor3x3_repr_basis_to_spherical_basis()

        print("Change of basis Wigner <-> rot")
        self._test_change_basis_wigner_to_rot()
        self._test_change_basis_wigner_to_rot()
        self._test_change_basis_wigner_to_rot()

        print("Spherical harmonics are solution of Y(rx) = D(r) Y(x)")
        for l__ in range(7):
            self._test_spherical_harmonics(l__)

        print("Irreducible repr are indeed representations")
        for l__ in range(7):
            self._test_is_representation(partial(irr_repr, l__))

        print("Reduce tensor product")
        self._test_reduce_tensor_product([(1, 0)], [(2, 0)])
        self._test_reduce_tensor_product([(3, 1), (2, 2)], [(2, 0), (1, 1), (1, 3)])


unittest.main()