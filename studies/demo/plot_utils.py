import pandas as pd 

import plotly.express as px
import plotly.subplots
import plotly.graph_objects as go


def make_scatter_power_vs_size_for_fixed_mde(
    df_stats, difference_percent, kpi, x='mean', y='power', color='n_weeks'
    ):

    # get data for plotting
    df_plot = df_stats[  df_stats['difference_percent']==difference_percent]
    color_vals = df_plot.pop(color)
    df_plot[color] = color_vals.astype('O')

    fig = px.scatter(
        df_plot, x='mean', y='power', color='n_weeks', 
        hover_data=df_plot[['regions', 'regions_size', 'n_weeks']], opacity=0.7
    )
    fig.update_layout( 
        title_text=f"{kpi}: power for MDE of {difference_percent}%",
        showlegend=True, xaxis_title=f'{kpi} (daily avg.)', paper_bgcolor='rgba(0,0,0,0)',
    )
    
    return fig 