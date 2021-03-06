import numpy as np
import pandas as pd
import os
import src

# from sklearn.linear_model import LinearRegression


def estimate_models(data, models, return_residuals=False):
    '''Estimates factor betas and alphas for a input returns data
    and a given set of models.
    '''
    df_period = pd.DataFrame(index=data.columns)
    df_residuals = pd.DataFrame(index=data.stack(dropna=False).index)
    for name, model in models.items():
        model_ = model.fit(data)
        model_estimates = model_.estimates
        if return_residuals:
            df_residuals[name] = model_.residuals.stack(dropna=False).values
        model_estimates.columns = [name+'_'+column for column in model_estimates.columns]
        df_period = df_period.join(model_estimates)
    if return_residuals:
        return df_period, df_residuals
    else:
        return df_period

def decompose_variance(variances, betas, factor_variances):
    '''Returns a DataFrame containing idiosyncratic variances for each period.'''
    # systematic variance
    if isinstance(factor_variances, pd.Series):
        factor_variances = factor_variances.to_frame()
    k_factors = factor_variances.shape[1]
    systematic_var = factor_variances @ betas.values.reshape(k_factors, -1)**2
    systematic_var.columns = variances.columns
    
    # idiosyncratic variance
    idio_var = variances - systematic_var
    idio_var[idio_var<=0] = np.nan
    
    # output
    decomposition = variances.stack(dropna=False).rename('total').to_frame()
    decomposition['systematic'] = systematic_var.stack(dropna=False).values
    decomposition['idiosyncratic'] = idio_var.stack(dropna=False).values
    
    return decomposition
    
    

# def estimate_factor_model(returns, factors):
#     '''Returns a DataFrame containing alpha and beta estimates.'''
#     # stack y
#     y = returns.T.stack(dropna=False)
#     keep_row = y.notna().values
#     y = y.loc[keep_row]

#     # build X
#     n_series = returns.shape[1]
#     block = factors.copy()
#     block.insert(loc=0, column='const', value=1)
#     X = np.kron(np.eye(n_series), block)[keep_row]

#     # fit
#     lm = LinearRegression(fit_intercept=False).fit(X, y)

#     # collect
#     k_factors = factors.shape[1]
#     columns = ['alpha'] + factors.columns.to_list()
#     estimates = pd.DataFrame(data=lm.coef_.reshape(n_series, k_factors+1),
#                              index=returns.columns, columns=columns)
#     return estimates

# def decompose_vola(volas, betas, factor_vola):
#     '''Returns a DataFrame containing idiosyncratic volatilities.'''
#     # systematic variance
#     k_factors = factor_vola.shape[1]
#     systematic_var = factor_vola**2 @ betas.values.reshape(k_factors, -1)**2
#     systematic_var.columns = volas.columns
    
#     # idiosyncratic vola
#     idio_var = volas**2 - systematic_var
#     idio_var[idio_var<=0] = np.nan
#     idio_vola = (idio_var**0.5)
#     return (idio_var, idio_vola)

# def idiosyncratic_vola(year, steps=2):
#     ''''''
#     # setup
#     index = src.loader.load_year(year, data='returns').columns
#     df_estimates = pd.DataFrame(index=index)
    
#     for step in range(steps):
#         # load
#         df_returns = src.loader.load_year(year, data='returns', data_year=year+step)
#         df_volas = src.loader.load_year(year, data='volas', data_year=year+step)
#         df_spy_ret = src.loader.load_spy_returns(year+step)
#         df_spy_vola = src.loader.load_spy_vola(year+step)
#         rf = src.loader.load_rf(year+step)

#         # estimate
#         estimates = estimate_factor_model(df_returns.subtract(rf.values), df_spy_ret.subtract(rf.values))
    
#         # decompose
#         idio_var, idio_vola = decompose_vola(df_volas, estimates['ret'], df_spy_vola)
    
#         # save
#         idio_var.to_csv('../data/processed/annual/{}/idio_var_{}.csv'.format(year, year+step))
#         idio_vola.to_csv('../data/processed/annual/{}/idio_vola_{}.csv'.format(year, year+step))
#         df_estimates = df_estimates.join(estimates, rsuffix='_t+{}'.format(step))
        
#     return df_estimates