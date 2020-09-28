import numpy as np
import scipy as sp

from sklearn.linear_model import LinearRegression
from sklearn.model_selection import PredefinedSplit
from sklearn.model_selection import GridSearchCV

from src.net import ElasticNet

class FAVAR:
    '''Factor augmented vector autoregression.'''
    
    def __init__(self, var_data, factor_data, p_lags=1):
        self.var_data = var_data
        self.factor_data = factor_data
        self.p_lags = p_lags
        self._check_dims()
        
    @property
    def t_periods(self):
        '''Returns the number of periods used for estimation.'''
        t_periods = self.var_data.shape[0]-self.p_lags
        return t_periods
    
    @property
    def n_series(self):
        '''Returns the number of series in the VAR.'''
        n_series = self.var_data.shape[1]
        return n_series
    
    @property
    def k_factors(self):
        '''Returns the number of factors used in the FAVAR.'''
        k_factors = self.factor_data.shape[1]
        return k_factors
    
    def _build_y(self):
        '''Returns a numpy array containing the dependent
        variable reshaped for estimation.
        '''
        y = self.var_data.values[self.p_lags:].reshape(-1,1, order='F')
        return y
    
    def _build_X_block(self):
        '''Returns a numpy array consisting of:
        - a vector of ones
        - the factors data
        - the series data for VAR estimation
        '''    
        # block components
        ones = np.ones([self.t_periods, 1])
        factors = self.factor_data[self.p_lags:]
        
        # first lag
        var = self.var_data[self.p_lags-1:-1]
        #print(var.iloc[0])
        # higher lags
        if self.p_lags > 1:
            for l in range(self.p_lags-1):
                #print(self.var_data[self.p_lags-2-l:-2-l])
                var = np.concatenate([var, self.var_data[self.p_lags-2-l:-2-l]], axis=1)
    
        # block
        X_block = np.concatenate([ones, factors, var], axis=1)
        return X_block
    
    def _build_X(self):
        '''Returns sparsediagonal block matrix with independent variables.'''    
        # build
        X_block = self._build_X_block()
        X = sp.sparse.kron(sp.sparse.eye(self.n_series), X_block, format='csc')
        return X
    
    def _build_X_y(self):
        '''Returns data matrices for estimation'''
        self._check_dims()
        X  = self._build_X()
        y = self._build_y()
        return (X, y)
    
    def _check_dims(self):
        '''Checks if data shapes match.'''
        assert self.var_data.shape[0] == self.factor_data.shape[0], \
            'data needs to have same time dimension'
    
    def fit_OLS(self, return_model=False):
        '''Fits the FAVAR coefficients using OLS.'''
        # build inputs
        X, y = self._build_X_y()
        
        # estimate
        model = LinearRegression(fit_intercept=False)
        model.fit(X, y)
        
        if return_model:
            return model
        else:
            self.coef_ =  model.coef_.ravel()
    
    def fit_elastic_net(self, alpha, lambdau, penalty_weights=None, return_model=False, **kwargs):
        '''Fits the FAVAR coefficients using the glmnet routine.'''
        # build inputs
        X, y = self._build_X_y()
        
        # estimate
        model = ElasticNet(alpha=alpha, lambdau=lambdau, intercept=False, standardize=False, **kwargs)
        model.fit(X, y, penalty_weights=penalty_weights)
        
        if return_model:
            return model
        else:
            self.coef_ =  model.coef_.ravel()
        
    @property
    def m_features(self):
        '''Returns the number of independent variables.'''
        m_features = 1 + self.k_factors + self.n_series*self.p_lags
        return m_features
    
    def penalty_weights(self, method='OLS', **kwargs):
        '''Returns estimated penalty weights.'''
        # estimate
        if method == 'OLS':
            coefficients = self.fit_OLS(return_model=True).coef_
        elif method == 'ElasticNet':
            coefficients = self.fit_elastic_net(return_model=True, **kwargs).coef_
        else:
            raise NotImplementedError('method not implemented.')

        # make list of non-penalised parameters
        steps = self.m_features
        zero_penalty_indices = list(np.concatenate([np.arange(0,1+self.k_factors)+steps*i for i in range(self.n_series)]))

        # create output
        penalty_weights = abs(coefficients.ravel())**-1
        penalty_weights[zero_penalty_indices] = 0
        return penalty_weights
    
    @property
    def intercepts(self):
        '''Returns a numpy array of intercepts.'''
        indices = [self.m_features*i for i in range(self.n_series)]
        intercepts = self.coef_[indices].reshape(-1,1)
        return intercepts
    
    @property
    def factor_betas(self):
        '''Returns a numpy array of factor betas.'''
        indices = list(np.concatenate([np.arange(1,1+self.k_factors)+self.m_features*i for i in range(self.n_series)]))
        beta_matrix = self.coef_[indices].reshape(self.n_series, self.k_factors)
        return beta_matrix
    
    @property
    def var_1_matrix(self):
        '''Returns a numpy array of first lag VAR coefficients.'''
        indices = list(np.concatenate([np.arange(1+self.k_factors, 1+self.k_factors+self.n_series)+self.m_features*i for i in range(self.n_series)]))
        var_matrix = self.coef_[indices].reshape(self.n_series, self.n_series)
        return var_matrix
    
    @property
    def var_matrices(self):
        '''Returns a list of numpy arrays with VAR coefficients.'''
        var_matrices = []
        for l in range(self.p_lags):
            indices = list(np.concatenate([np.arange(1+self.k_factors, 1+self.k_factors+self.n_series)+self.m_features*i+self.n_series*l for i in range(self.n_series)]))
            var_matrix = self.coef_[indices].reshape(self.n_series, self.n_series)
            var_matrices += [var_matrix]
        return var_matrices
    
    @property
    def residuals_(self):
        '''Returns the residual matrix to a vectorised VAR model.'''
        X, y = self._build_X_y()
        
        residuals = y - X.dot(self.coef_.reshape(-1, 1))
        residual_matrix = residuals.reshape(-1, self.n_series, order='F')
        return residual_matrix
    
    def make_cv_splitter(self, splits=10):
        '''Returns a PredefinedSplit object for cross validation.'''
    
        # shapes
        length = self.t_periods // splits
        resid = self.t_periods % splits

        # build single series split
        single_series_split = []
        for i in range(splits-1, -1 , -1):
            single_series_split += length*[i]
            if i < resid:
                single_series_split += [i]
            
        # make splitter object
        split = self.n_series*single_series_split
        splitter = PredefinedSplit(split)
        return splitter
    
    def fit_elastic_net_cv(self, grid, splits=10, return_cv=False, weighting_method='OLS', **kwargs):
        '''Fits the FAVAR coefficients using the glmnet routine.
        Currently uses OLS inferred penalty weights.
        '''
        # build inputs
        X, y = self._build_X_y()
        penalty_weights = self.penalty_weights(method=weighting_method)
        split = self.make_cv_splitter(splits=splits)
        elnet = ElasticNet(intercept=False, standardize=False)
        
        # estimate
        cv = GridSearchCV(elnet, grid, cv=split, n_jobs=-1, verbose=1, **kwargs)
        cv.fit(X, y, penalty_weights=penalty_weights)

        if return_cv:
            return cv
        else:
            self.coef_ =  cv.best_estimator_.coef_.ravel()

        
######################################################################################################################################################



def data_dimensions(df_est, factors_est):
    '''Returns the data dimensions for the estimation.'''
    t_periods = df_est.shape[0]-1
    n_series = df_est.shape[1]
    k_factors = factors_est.shape[1]
    return (t_periods, n_series, k_factors)

def build_y(df_est, lag=1):
    '''Returns a numpy array containing the dependent
    variable reshaped for estimation.
    '''
    dependent = df_est.values[lag:].reshape(-1,1, order='F')
    return dependent

def build_X_block(df_est, factors_est, lag=1):
    '''Returns a numpy array consisting of:
    - a vector of ones
    - the factors data
    - the series data for VAR estimation
    '''
    # dims
    t_periods = df_est.shape[0]-lag
    
    # block components
    ones = np.ones([t_periods, 1])
    factors = factors_est[lag:]
    var = df_est[:-lag].values
    
    # block
    X_block = np.concatenate([ones, factors, var], axis=1)
    return X_block

def build_X(df_est, factors_est, lag=1):
    '''Returns sparsediagonal block matrix with independent variables.'''
    # dims
    n_series = df_est.shape[1]
    
    # build
    X_block = build_X_block(df_est=df_est, factors_est=factors_est, lag=lag)
    independent = sp.sparse.kron(sp.sparse.eye(n_series), X_block, format='csc')
    return independent

def build_matrices(df_est, factors_est, lag=1):
    '''Returns data matrices for estimation'''
    assert df_est.shape[0] == factors_est.shape[0], \
        'data needs to have same time dimension'
    y = build_y(df_est=df_est, lag=lag)
    X  = build_X(df_est=df_est, factors_est=factors_est, lag=lag)
    return (y, X)

def ols_penalty_weights(X, y, n_series, k_factors=1, has_intercepts=True):
    '''Returns penalty wwights from OLS estimates.'''
    # fit OLS model
    lm = LinearRegression(fit_intercept=False)
    lm.fit(X, y)
    
    # make list of non-penalised parameters
    steps = has_intercepts + k_factors + n_series
    zero_penalty_indices = list(np.concatenate([np.arange(0,1+k_factors)+steps*i for i in range(n_series)]))

    # create output
    penalty_weights = abs(lm.coef_.ravel())**-1
    penalty_weights[zero_penalty_indices] = 0
    return penalty_weights


def format_coefficients(coefficients, k_factors, n_series):
    '''Returns formatted coefficient arrays'''
    
    steps = 1 + k_factors + n_series
    
    # intercepts
    intercept_indices = [0+steps*i for i in range(n_series)]
    intercepts = coefficients[intercept_indices].reshape(-1,1)
    
    # intercepts
    beta_indices = list(np.concatenate([np.arange(1,1+k_factors)+steps*i for i in range(n_series)]))
    beta_matrix = coefficients[beta_indices].reshape(n_series,k_factors)
    
    # var coefficients
    var_indices = list(np.concatenate([np.arange(1+k_factors,steps)+steps*i for i in range(n_series)]))
    var_matrix = coefficients[var_indices].reshape(n_series,n_series)
    
    return (intercepts, beta_matrix, var_matrix)


def residual_matrix(y, X, coefficients, n_series):
    '''Returns the residual matrix to a vectorised VAR model.'''
    residuals = y - X.dot(coefficients)
    residual_matrix = residuals.reshape(-1, n_series, order='F')
    return residual_matrix