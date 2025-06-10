import itertools
from datetime import timedelta
from typing import Union

import pandas as pd


def sanitise_header(df: pd.DataFrame) -> None:
    """Sanitise header of pandas dataframe `df`. All columns are transformed into:
    - lowercase
    - spaces and '-' are replaced by '_'
    - removes `.,$%^&£@#()[]}{`

    Examples:
    >>> df = pd.DataFrame(data=[[1, 2], [3, 4]], columns=["Impr.  A.", "price [$]"])
    >>> sanitise_header(df)
    >>> list(df.columns)
    ['impr_a', 'price']
    """

    char_remove = list('.,$%^&£@#()[]}{?')
    char_replace = list('- ')

    translation_table = str.maketrans(
        {k: '_' for k in char_replace} | {k: '' for k in char_remove}
    )

    columns_original = df.columns
    columns_new = [c.lower().translate(translation_table) for c in df.columns]

    # remove '_' at start/end, or multiple '_' in sequence
    columns_new = [
        '_'.join([x for x in c.split('_') if x != '']) for c in columns_new
    ]

    if len(set(columns_new)) < len(columns_new):
        raise ValueError('columns with same name found.')

    df.columns = columns_new


def add_unique_dates(
    df: pd.DataFrame, col_time: str, freq_days: int = 1, groupby: list = None
) -> pd.DataFrame:
    """Given a dataframe df` with column `col_time` containing `datetime64[ns]`,
    this function will:
    - Check that no duplicate dates exist in `df[col_time]` (within the combinations specified by `groupby`).
    - Include (if missing) all dates in the range [df[col_time].min(), df[col_time].max()], with
    a frequency of `freq_days` in between dates. Dates are replicated between the categories specified
    by `groupby`.
    - Check that no dates are lost in the process. This can happen if (say) you want to create
    a range of weekly dates (starting on Mon), but the function finds that some dates refer
    to a day other than Mon. In this case, the function will return `ValueError` and ask to
    aggregate in a format consistent with `freq_days`.

    The function will returns a new dataframe.
    Note: if rows are added as a result of this operation, null values will be found
    under all columns other than `col_time`. A warning is issued in this case.

    Example:
    >>> df = pd.DataFrame(
    ...    {'dates': pd.to_datetime(['2022-03-05', '2022-03-09']), 'a': [1, 3]}
    ... )
    >>> add_unique_dates(df, 'dates', 2)
           dates    a
    0 2022-03-05  1.0
    1 2022-03-07  NaN
    2 2022-03-09  3.0


    >>> df = pd.DataFrame({
    ...     'dates': pd.to_datetime(['2022-03-05', '2022-03-07', '2022-03-05']),
    ...     'sales': [1, 3, 2],
    ...     'product': ['car', 'car', 'plane'],
    ... })
    >>> add_unique_dates(df, 'dates', 2, groupby=['product'])
           dates product  sales
    0 2022-03-05     car    1.0
    1 2022-03-05   plane    2.0
    2 2022-03-07     car    3.0
    3 2022-03-07   plane    NaN
    """

    if groupby:
        assert set(groupby) < set(
            df.columns
        ), 'Items in `groupby` must be columns of `df`'
        check_duplicates_obj = df.groupby(by=groupby)
    else:
        groupby, check_duplicates_obj = [], df

    # check for duplicate dates
    if check_duplicates_obj[col_time].value_counts().max() > 1:
        raise ValueError('Duplicate dates found in `col_time`.')

    # create unique combinations of dates
    dates_rng = pd.date_range(
        df[col_time].min(),
        df[col_time].max(),
        freq=timedelta(days=freq_days),
    )

    # check all original dates are a subset of new dates. If not we raise an error as:
    # 1. original dates are not in the intended frequency;
    # 2. we don't know how to transform/compute KPIs on the wanted dates `df_range[col_time]`
    # 3. therefore, we either have to drop some rows in df, or output a dataframe that is
    # not on the right dates grid.
    if not (set(df[col_time].unique()) <= set(dates_rng.unique())):
        raise ValueError(
            'Dates in `col_time` are not given at the frequency pecified in `freq_days`.'
        )

    # Define range dataset and repeat it across all combinations of values in
    # the columns specified by `groupby`
    combinations = {col_time: dates_rng} | {c: df[c].unique() for c in groupby}
    df_range = pd.DataFrame(
        data=itertools.product(*combinations.values()),
        columns=combinations.keys(),
    )

    return (
        df_range.merge(df, on=list(combinations.keys()), how='left')
        .sort_values(by=col_time)
        .reset_index(drop=True)
    )


def check_all_dates(
    series_of_dates: pd.Series, freq: int = 1, check_duplicates: bool = True
):
    """Check that a pandas series contains all dates in a range and (optionally)
    checks for duplicates. Raises a `ValueError`

    :param pd.Series series_of_dates: Series to check.
    :param int freq: Expected frequency of dates (e.g. for weekly dates, `freq=7`); defaults to 1.
    :param bool check_duplicates: if True, also checks the series has no duplicates.
    """

    # compute, and check, the number of expected dates in the series
    n_days_diff = (series_of_dates.max() - series_of_dates.min()).days

    # from IPython import embed

    # embed()

    if (n_days_diff) % freq != 0:
        raise ValueError(
            'First and last datetime in series do not match expected frequency!'
        )
    n_dates_expected = n_days_diff // freq + 1

    if series_of_dates.nunique() < n_dates_expected:
        raise ValueError('Missing dates in series!')
    if check_duplicates and (len(series_of_dates) > n_dates_expected):
        raise ValueError('Duplicate dates in series!')


def get_week_starts(s: pd.Series, day_week_starts: str = 'Monday'):
    if day_week_starts != 'Monday':
        raise ValueError("""Only accepts day_week_starts = 'Monday'.""")

    weekday = s.dt.weekday
    return s - pd.to_timedelta(weekday % 7, unit='d')


def aggregate_weekly(
    df: pd.DataFrame,
    col_date: str,
    aggregration_functions: Union[dict, callable],
    day_week_starts: str = 'Monday',
    drop_incomplete_weeks: bool = True,
):
    """Aggregate dataframe of historic daily data weekly.

    :param pd.DataFrame df: input dataframe.
    :param str col_date: column of dates.
    :param Union[dict, callable] aggregration_functions: aggregation function(s).
        Any input accepted by `pandas.DataFrame.aggregate` will do.
    :param str day_week_starts: Day of week (starting with capital) when week
        should begind; defaults to 'Monday'.
    :param bool drop_incomplete_weeks: If true, will discard weeks for which not
        all dates were provided; defaults to True
    :raises ValueError: If dataframe if not in the right format.
    :return _type_: a dataframes where dta are aggreated weekly. The dataframe
        has same columns as input, but the column `col_date` now contains only
        start of the week.
    """

    # ensure we are not (say) passing monthly data or doing something stupid.
    check_all_dates(df[col_date], freq=1, check_duplicates=True)

    col_wk_starts = '__' + col_date + '__wk_starts'
    col_days_in_wk = '__' + col_date + '__days_wk'

    # Finally, aggregate weekly (and remove incomplete weeks)
    df[col_wk_starts] = get_week_starts(df[col_date], day_week_starts)
    df[col_days_in_wk] = df.groupby(col_wk_starts).transform('count')[col_date]
    df = df[df[col_days_in_wk] == 7].reset_index(drop=True)
    if drop_incomplete_weeks:
        df = df.drop(columns=[col_date, col_days_in_wk])

    # group by weekly (+ check week starts on a monday)
    df = df.groupby(col_wk_starts).agg(aggregration_functions).reset_index()
    df = df.rename(columns={col_wk_starts: col_date})

    # df.drop(col_days_in_wk, inplace=True)

    if set(df[col_date].dt.day_name().unique()) != {'Monday'}:
        raise ValueError('Some weeks do not start on Monday')

    return df


if __name__ == '__main__':
    import doctest

    doctest.testmod()

    ### uncomment for interactive testing

    # # add unique dates (1)
    # df = pd.DataFrame(
    #     {'dates': pd.to_datetime(['2022-03-05', '2022-03-09']), 'a': [1, 3]}
    # )
    # add_unique_dates(df, 'dates', 2)

    # # make unique dates (2)
    # df = pd.DataFrame(
    #     {
    #         'dates': pd.to_datetime(
    #             ['2022-03-05', '2022-03-07', '2022-03-05']
    #         ),
    #         'sales': [1, 3, 2],
    #         'product': ['car', 'car', 'plane'],
    #     }
    # )
    # add_unique_dates(df, 'dates', 2, groupby=['product'])

    # # check sanitise
    # df = pd.DataFrame(
    #     data=[[1, 2], [3, 4]], columns=['Impr.  A.', 'price [$]']
    # )
    # sanitise_header(df)
    # list(df.columns)
