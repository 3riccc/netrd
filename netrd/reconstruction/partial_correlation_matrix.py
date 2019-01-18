"""
partial_correlation_matrix.py
---------------------

Reconstruction of graphs using the partial correlation matrix.

author: Stefan McCabe
email: stefanmccabe at gmail dot com
Submitted as part of the 2019 NetSI Collabathon

"""
from .base import BaseReconstructor
import numpy as np
import networkx as nx
from scipy import stats, linalg


class PartialCorrelationMatrixReconstructor(BaseReconstructor):
    def fit(self,
            TS,
            index=None,
            drop_index=True,
            of_residuals=False,
            cutoffs=[(-1, 1)]):
        """
        Reconstruct a network from time series data using a regularized
        form of the precision matrix. After [this tutorial](
        https://bwlewis.github.io/correlation-regularization/) in R.

        Params
        ------
        index (int, array of ints, or None): Take the partial correlations of
        each pair of elements holding constant an index variable or set of
        index variables. If None, take the partial correlations of the
        variables holding constant all other variables.
        drop_index (bool): If True, drop the index variables after calculating
        the partial correlations.
        of_residuals (bool): If True, after calculating the partial correlations (
        presumably using a dropped index variable), recalculate the partial
        correlations between each variable, holding constant all other variables.
        cutoffs (list of tuples): When thresholding, include only edges whose
        correlations fall within a given range or set of ranges. The lower
        value must come first.

        Returns
        -------
        G: a reconstructed graph.

        """

        p_cor = partial_corr(TS, index=index)

        if drop_index and index is not None:
            p_cor = np.delete(p_cor, index, axis=0)
            p_cor = np.delete(p_cor, index, axis=1)

        if of_residuals:
            p_cor = partial_corr(p_cor, index=None)

        self.results['matrix'] = p_cor

        mask_function = np.vectorize(lambda x: any([x>=cutoff[0] and x<=cutoff[1] for cutoff in cutoffs]))
        mask = mask_function(p_cor)

        # use the mask to threshold the correlation matrix
        A = p_cor * mask

        # construct the network
        self.results['graph'] = nx.from_numpy_array(A)
        G = self.results['graph']

        return G


# This partial correlation function is adapted from Fabian Pedregosa-Izquierdo's
# implementation of partial correlation in Python, found at [this gist](
# https://gist.github.com/fabianp/9396204419c7b638d38f)
"""
Partial Correlation in Python (clone of Matlab's partialcorr)

This uses the linear regression approach to compute the partial 
correlation (might be slow for a huge number of variables). The 
algorithm is detailed here:

    http://en.wikipedia.org/wiki/Partial_correlation#Using_linear_regression

Taking X and Y two variables of interest and Z the matrix with all the variable minus {X, Y},
the algorithm can be summarized as

    1) perform a normal linear least-squares regression with X as the target and Z as the predictor
    2) calculate the residuals in Step #1
    3) perform a normal linear least-squares regression with Y as the target and Z as the predictor
    4) calculate the residuals in Step #3
    5) calculate the correlation coefficient between the residuals from Steps #2 and #4; 

    The result is the partial correlation between X and Y while controlling for the effect of Z


Date: Nov 2014
Author: Fabian Pedregosa-Izquierdo, f@bianp.net
Testing: Valentina Borghesani, valentinaborghesani@gmail.com
"""


def partial_corr(C, index=None):
    """Returns the sample linear partial correlation coefficients between pairs of
    variables in C, controlling for the remaining variables in C.


    Parameters
    ----------
    C : array-like, shape (p, n)
        Array with the different variables. Each row of C is taken as a variable


    Returns -------
    P : array-like, shape (p, p)
        P[i, j] contains the partial correlation of C[:, i] and C[:, j]
        controlling for the remaining variables in C.

    """

    C = np.asarray(C).T
    p = C.shape[1]
    P_corr = np.zeros((p, p), dtype=np.float)

    for i in range(p):
        P_corr[i, i] = 1
        for j in range(i + 1, p):
            if index is None:
                idx = np.ones(p, dtype=np.bool)
                idx[i] = False
                idx[j] = False
            elif type(index) is int or \
            (isinstance(index, np.ndarray) and
             issubclass(index.dtype.type, np.integer)):
                idx = np.zeros(p, dtype=np.bool)
                idx[index] = True
            else:
                raise ValueError("Index must be an integer, an array of "
                                 "integers, or False.")

            beta_i = linalg.lstsq(C[:, idx], C[:, j])[0]
            beta_j = linalg.lstsq(C[:, idx], C[:, i])[0]

            res_j = C[:, j] - C[:, idx].dot(beta_i)
            res_i = C[:, i] - C[:, idx].dot(beta_j)

            corr = stats.pearsonr(res_i, res_j)[0]
            P_corr[i, j] = corr
            P_corr[j, i] = corr

    return P_corr
