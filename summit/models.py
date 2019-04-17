from abc import ABC, abstractmethod

from GPy.models import GPRegression
from GPy.kern import Matern52
import numpy as np

class Model(ABC):
    
    @abstractmethod
    def fit(self, X, Y):
        pass

    @abstractmethod
    def predict(self, X):
        pass

class GPyModel(Model):
    def __init__(self, kernel=None, noise_var=1.0, optimizer=None):
        if kernel:
            self._kernel = kernel
        else:
            input_dim = self.domain.num_continuous_dimensions() + self.domain.num_discrete_variables(), 
            self._kernel =  Matern52(input_dim = input_dim, ARD=True)
        self._noise_var = noise_var
        self._optimizer = optimizer
    
    def fit(self, X, Y, num_restarts=10, max_iters=2000):
        self._model = GPRegression(X,Y, self._kernel, noise_var=self._noise_var)
        if self._optimizer:
            self._model.optimize_restarts(num_restarts = num_restarts, 
                                         verbose=False,
                                         max_iters=max_iters,
                                         optimizer=self._optimizer)
        else:
            self._model.optimize_restarts(num_restarts = num_restarts, 
                                         verbose=False,
                                         max_iters=max_iters)

    def predict(self, X):
        m, v = self._model.predict(X)
        return m,v 
    
    def spectral_posterior_sample(self, n_spectral_points): 
        '''Take sample function from posterior GP'''

        Xnew = self._model.X
        Ynew = self._model.Y

        # Get variables from problem structure
        n, D = np.shape(Xnew)
        ell = self._model.kern.lengthscale.values
        sf2 = self._model.kern.variance.values[0]
        sn2 = np.exp(OptGP.hyp.log_noise_level)

        # Monte carlo samples of W and b
        sW1 = lhs(D, n_spectral_points)
        sW2 = sW1

        p = matlib.repmat(np.divide(1, ell), n_spectral_points, 1)
        q = np.sqrt(np.divide(OptGP.matern_nu, chi2inv(sW2, OptGP.matern_nu)+1e-7)) #Add padding to prevent /0 errors
        q.shape = (n_spectral_points, 1)
        W = np.multiply(p, norm.ppf(sW1))
        W = np.multiply(W, q)

        b = lhs(n_spectral_points, 1)
        b = 2*np.pi*b.transpose()

        # Calculate phi
        phi = np.sqrt(2*sf2/n_spectral_points)*np.cos(W@Xnew.transpose() +  matlib.repmat(b, 1, n))

        #Sampling of theta according to phi
        A = phi@phi.transpose() + sn2*np.identity(n_spectral_points)
        invA = inv_cholesky(A)
        mu_theta = invA@phi@Ynew
        cov_theta = sn2*invA
        cov_theta = 0.5*(cov_theta+cov_theta.transpose())
        theta = np.random.multivariate_normal(mu_theta, cov_theta)
        theta.shape = (n_spectral_points, D)

        #Posterior sample according to theta
        def f(x):
            inputs, _ = np.shape(x)
            bprime = matlib.repmat(b, 1, inputs)
            output =  (theta.transpose()*np.sqrt(2*sf2/n_spectral_points))@np.cos(W*x.transpose()+ bprime)
            return output.transpose()

        return f