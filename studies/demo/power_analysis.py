import logging
import copy 
import itertools
from typing import Union
import collections
import warnings 

import pandas as pd 
import numpy as np 

import causalinf

import sys, os

import pandas_utils as pu


# Parameters Utils
logging.basicConfig(encoding='utf-8', level=logging.INFO)
logger = logging.getLogger(__name__)


def select_candidate_regions(
    df: pd.DataFrame,
    candidate_regions_set: collections.abc.Set,
    max_combinations: int, 
    max_group_size: int,
    alpha: float, 
    n_obs: int, 
    alternative: str,
    power: float = None, 
    difference_percent: float = None, 
    df_profiles: pd.DataFrame = None,
    size_bounds_frac: tuple[float,float] = None,
    log_frequency: int = 100,
) -> pd.DataFrame:
    """For each possible combination of regions in `candidate_regions_set` (test 
    region), this  functions runs a power analysis / minimum detectable effect (MDE) assumint 
    that an experiment is run in the test regions so defined. Test regions are
    further downselected so as to meet specific criteria (e.g. min/max size).

    Args:
        df (pd.DataFrame): Dataset with time series data of KPI in candidate regions.
            Each column of `df` is a region. Any other metric (e.g. date) must 
            be set as an index.
        candidate_regions_set (collections.abc.Set): Candidate regions. Must be a 
            subset of `df.columns`
        max_combinations (int): Maximum number of combinations tried.
        max_group_size (int): Maximum size of each candidate region set.
        params_stat (dict): Parameters for statistical analysis.
        alpha (float): Significance level for power analysis.
        n_obs (int): Number of observations for power analysis.
        alternative (str): alternative. Must be ['larger', 'two-sided', 'smaller'].
        power (float, optional): Statistical power. If None, `difference_percent` 
            must be passed as input, and the analysis will compute test power for
            each test region. Defaults to None.
        difference_percent (float, optional): Minimum percentage difference to
            be detected by the test (aka Minimum detectable effect, MDE). If None, 
            `power` must be passed as an input, and the analysis will compute the 
            MDE for each test region. Defaults to None.
        df_profiles (pd.DataFrame). Profiles dataframe. The index of the dataframe
            are the geo regions in `df.columns`. Defaults to None.
        size_bounds_frac (tuple[float,float], optional): Bounds for test region
            size, expressed as a fraction of all regions in `df` (i.e. of the 
            whole market),  and not as a fraction of regions suitable for 
            experimentations (`candidate_regions_set`), which is less interpretable. 
            Defaults to None.
        log_frequency (int): Frequency for logging updates.

    Returns:
        pd.DataFrame: Dataframe with candidate regions and key stats for each of
        them.
    """    

    if (difference_percent is None) and (power is None):
        raise ValueError('One between `difference_percent` and `power` must be passed as an input.')
    if (difference_percent is not None) and (power is not None):
        raise ValueError('Only one between `difference_percent` and `power` must be passed as an input.')
    if alpha<=0.0 or alpha>=1.0:
        raise ValueError('`alpha` must be in (0,1)')
    if size_bounds_frac:
        if len(size_bounds_frac)!=2:
            raise ValueError('`size_bounds_frac` must have length 2.')
        if (size_bounds_frac[0]>=size_bounds_frac[1]):
            raise ValueError('`size_bounds_frac[0]` must be smaller than `size_bounds_frac[1]`.')


    def to_list(kwarg):
        if isinstance(kwarg, list):
            return kwarg
        return [kwarg]

    list_of_params_stats = []
    for (_alpha, _power, _n_obs, _difference_percent) in itertools.product( 
        to_list(alpha), to_list(power), to_list(n_obs), to_list(difference_percent)):
        list_of_params_stats.append(dict(
            alpha=_alpha, power=_power, n_obs=_n_obs, difference_percent=_difference_percent
            )
        )

    # regions size
    # Note: when computing the (fractional) size of each region, we intentionally 
    # include all regions (including those not in `candidate_regions_set`). This 
    # allows the user to set realistic boundaries based on fraction of the whole 
    # market (and not based on a fraction of candidate test regions).
    df_regions_size = df.sum(axis=0)
    df_regions_size /= df_regions_size.sum()
    df_regions_size = df_regions_size.to_frame(name='__size__')
    assert '__size__' not in df.columns, 'Column `__size__` not allowed in `df`.' 

    # print('DEBUG: region size')    
    # print(df_regions_size)

    # compute global profile
    if df_profiles is not None:
        if set(df.columns) != set(df_profiles.index):
            # Check regions for which a profile is provided, match the regions in df.
            # TODO: improve this to check regions with a profile make up for at east X% of total.
            raise ValueError('`df_profiles` index much contain all, and only, the columns of `df`')

        # prepare profile dataset (also for future calculations)
        cols_profile = df_profiles.columns
        df_profiles = df_profiles.join(df_regions_size, how='inner')
        for col in cols_profile:
            df_profiles[col+'__weighted__'] = df_profiles['__size__']*df_profiles[col]
        
        # compute reference profile
        if not np.isclose(df_profiles['__size__'].sum(), 1.0, atol=0.02):
            warnings.warn('Regions size do not add up to 1. Reference profile may not be accurate.')
        scaler = df_profiles['__size__'].sum()
        df_profile_ref = pd.Series({
            col: df_profiles[col+'__weighted__'].sum()/scaler for col in cols_profile
        }) 

    data = []
    counter, regions_number = 0, 0
    while regions_number < max_group_size:
        regions_number += 1
        logger.info(f"Starting exploring group size {regions_number}")

        # This is repeated below, as here is a nested for loop.
        if counter >= max_combinations:
            logging.info(f'Maximum number of combinations ({counter}) reached. The search is terminated.')
            regions_number = max_group_size+1
            break

        # Loop not optimised!
        # Start from sets in regions_number - 1, and regions iteratively.
        for regions in itertools.combinations( candidate_regions_set, regions_number):

            # print(regions)
            counter += 1

            # check region meets requisites
            # TODO: add similarity check here
            regions_size = df_regions_size.filter(items=regions, axis=0)['__size__'].sum()
            if size_bounds_frac:
                if (regions_size>=size_bounds_frac[1] or
                    regions_size<=size_bounds_frac[0]):
                    continue

            # add profile data (weighted sum of individual regions profiles)
            if df_profiles is not None:
                df_profile_regions = df_profiles.filter(items=regions, axis=0)
                scaler = df_profile_regions['__size__'].sum()
                profile_regions = {
                    col: df_profile_regions[col+'__weighted__'].sum()/scaler for col in cols_profile
                }
            else:
                profile_regions = dict()
                
            # aggregate
            vals =  df[list(regions)].sum(axis=1)
            mean_val, std_val = vals.mean(), vals.std()


            for params_stats in list_of_params_stats:
                stats = causalinf.ab.t_test.get_test_design_summary(
                    mean_null_hp = mean_val, std_null_hp = std_val, **params_stats
                )
                data.append(
                    {'regions': regions, 'regions_number': regions_number, 'regions_size': regions_size} |
                    stats | {'mean': mean_val, 'std': std_val} | 
                    profile_regions
                )

            # check termination/logging
            if counter % log_frequency == 0:
                logging.info(f'Explored {counter} combinations of regions.')
            
            if counter >= max_combinations:
                logging.info(f'Maximum number of combinations ({counter}) reached. The search is terminated.')
                regions_number = max_group_size+1
                break

    logging.info(f'Process completed. Tries {counter} combinations of regions. {len(data)} meeting criteria.')
    df_stats =  pd.DataFrame(data)

    # add delta from profile
    if df_profiles is not None:
        for col in cols_profile:
            df_stats[col + '__delta__'] = df_stats[col]-df_profile_ref[col]
            if not np.isclose(df_profile_ref[col],0,atol=1e-6):
                df_stats[col + '__delta_perc__'] = 1e2*df_stats[col + '__delta__']/df_profile_ref[col]

    return df_stats    
