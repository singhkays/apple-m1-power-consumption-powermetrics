#!./bin/python3
import os
import subprocess
import re
import csv
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import pandas as pd
import numpy as np
import time
import plotly.figure_factory as ff
from PIL import Image

def regexParse(content, videoType):
    # Declare local dataframes
    dfPower, dfFrequency, dfUsage = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Regex findall returns matches which are all strings
    # Used list(map(int, regexMatches))) to convert the list of strings to a list of int or float so that in Excel it's an integer
    dfPower['Efficiency Cluster'] = pd.Series(map(int, re.findall(r'E-Cluster Power:\s*([\d.]+)\s*mW', content)))
    dfFrequency['Efficiency Cluster'] = pd.Series(map(int, re.findall(r'E-Cluster HW active frequency:\s*([\d.]+)\s*MHz', content)))
    dfUsage['Efficiency Cluster'] = pd.Series(map(float, re.findall(r'E-Cluster HW active residency:\s*([\d.]+)%', content)))

    dfPower['Performance Cluster'] = pd.Series(map(int, re.findall(r'P-Cluster Power:\s*([\d.]+)\s*mW', content)))
    dfFrequency['Performance Cluster'] = pd.Series(map(int, re.findall(r'P-Cluster HW active frequency:\s*([\d.]+)\s*MHz', content)))
    dfUsage['Performance Cluster'] = pd.Series(map(float, re.findall(r'P-Cluster HW active residency:\s*([\d.]+)%', content)))

    dfPower['DRAM'] = pd.Series(map(int, re.findall(r'DRAM Power:\s*([\d.]+)\s*mW', content)))
    dfPower['Cluster'] = pd.Series(map(int, re.findall(r'Clusters Total Power:\s*([\d.]+)\s*mW', content)))
    dfPower['Package'] = pd.Series(map(int, re.findall(r'Package Power:\s*([\d.]+)\s*mW', content)))

    dfPower['GPU'] = pd.Series(map(int, re.findall(r'GPU Power:\s*([\d.]+)\s*mW\nPackage Power', content)))
    dfFrequency['GPU'] = pd.Series(map(int, re.findall(r'GPU active frequency:\s*([\d.]+)\s*MHz', content)))
    dfUsage['GPU'] = pd.Series(map(float, re.findall(r'GPU active residency:\s*([\d.]+)%', content)))

    # Other components power needs to be extracted out of total package power
    # e.g. result from logs
        # DRAM Power: 14 mW
        # Clusters Total Power: 30 mW
        # GPU Power: 14 mW
        # Package Power: 99 mW
    dfPower['Other'] = dfPower['Package'] - (dfPower['Cluster'] + dfPower['DRAM'] + dfPower['GPU'])

    # Check if the number of datapoints from all videos are equal
    if((len(dfPower) != len(dfFrequency)) or (len(dfPower) != len(dfUsage)) or (len(dfUsage) != len(dfFrequency))):
        print("The lengths of the dataframes are not equal. Check the regexes.") 
    else:
        dataPoints = len(dfPower)
        dfPower['time'] = dfFrequency['time'] = dfUsage['time'] = list(range(1, dataPoints + 1))
        dfPower['Video Type'] = dfFrequency['Video Type'] = dfUsage['Video Type'] = [videoType] * dataPoints

    return dfPower, dfFrequency, dfUsage

def buildVLCCharts(dfPower, dfFrequency, dfUsage, config, kLogo):

    fig = px.area(dfPower.loc[dfPower["Video Type"].isin(["4K-VP9-TEST", "4K-AV1", "FHD-AV1", "FHD-H264", "FHD-VP9"])], x='time', y=['Package'], template='plotly_dark', 
    width = 700, height = 350, facet_col='Video Type', line_shape= "spline", facet_col_wrap = 5,
    labels={"value": "Power Consumption (mW)", "time": "Time (s)"}, color_discrete_map={"Package": "#57FFBC"},
    category_orders={"Video Type": ["4K-VP9", "4K-AV1", "FHD-AV1", "FHD-H264", "FHD-VP9"]})
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(family="SF Pro Display, Roboto, Droid Sans, Arial", size=11)
    
    fig.update_yaxes(type='linear', title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424')
    fig.update_xaxes(showgrid=False, title_font = dict(size=10), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9))
    fig.update_traces(hovertemplate='%{y} (mW)', line_smoothing = 1.3)
    fig.update_layout(autosize = True, hovermode="x", 
        showlegend = False, font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Total Package Power Consumption over Time</b> <br> <sup> Apple Mac Mini M1 | VLC 3.0.12.1 (local files) | MacOS 11.2.2 </sup>",
            'y':0.92,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 50, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=1, y=0.79, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.12, y=1.17,
            sizex=0.2, sizey=0.2,
            xanchor="left", yanchor="bottom"
        )
    )

    fig.write_html("outputs/plotly-power-package.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-power-package.svg")

    # Figure for Total Power Over Time
    fig = px.line(dfPower.loc[dfPower["Video Type"].isin(["4K-VP9", "4K-AV1", "FHD-AV1", "FHD-H264", "FHD-VP9"])], x='time', y=['Efficiency Cluster', 'Performance Cluster', 'DRAM', 'GPU', 'Other'], template='plotly_dark', 
    width = 700, height = 1000, facet_row='Video Type', line_shape= "spline", render_mode = "svg",
    # color_discrete_sequence = px.colors.qualitative.G10,
    # color_discrete_sequence=px.colors.sequential.YlOrRd,
    # color_discrete_map={
    #     "Efficiency Cluster": "#AA0EFE",
    #     "Performance Cluster": "#1CBE50",
    #     "DRAM": "#57FFBC",
    #     "GPU": "#2ED9FF",
    #     # "Other": "rgb(95, 70, 144)"
    #     "Other": "#FBE426"
    # },
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels = {"value": "Power Consumption (mW)", "time": "Time (s)"}, 
    category_orders = {"Video Type": ["4K-VP9", "4K-AV1", "FHD-AV1", "FHD-H264", "FHD-VP9"]})

    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    for annotation in fig['layout']['annotations']: 
        # print(annotation)
        annotation['textangle'] = 0
        annotation['xanchor'] = 'right'
        annotation['x'] = annotation['x'] - 0.002
        annotation['y'] = annotation['y'] + 0.038
        annotation['font'] = dict(family="SF Pro Display, Roboto, Droid Sans, Arial", size=13)

    fig.update_yaxes(type='linear', title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424')
    fig.update_xaxes(showgrid=False, color="#707070", title_font_color = "#707070", tickfont = dict(size = 9))
    # fig.update_traces(hovertemplate='%{y} (mW)', line_smoothing = 1.3)
    fig.update_traces(hovertemplate='%{y} (mW)')
    fig.update_layout(legend_title_text='', autosize = True, hovermode="x", 
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Power Consumption over Time</b> <br> <sup> Apple Mac Mini M1 | VLC 3.0.12.1 (local files) | MacOS 11.2.2 </sup>",
            'y':0.97,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 30, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'left', yanchor = 'top', 
        x=0.01, y=0.965, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.119, y=1.038,
            sizex=0.065, sizey=0.065,
            xanchor="left", yanchor="bottom"
        )
    )

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-power-total.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-power-total.svg")

    # Figure for Total Power Over Time
    fig = px.line(dfPower.loc[dfPower["Video Type"].isin(["4K-VP9", "4K-AV1", "FHD-AV1", "FHD-H264", "FHD-VP9"])], x='time', y=['Efficiency Cluster', 'Performance Cluster', 'DRAM', 'GPU', 'Other'],  
    width = 700, height = 1000, facet_row='Video Type', render_mode = "svg")

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-power-total-2.html", include_plotlyjs="cdn")

    # BAR CHART FOR Averages by component
    # Pull out only the non-browser video types
    barDf = (dfPower.loc[dfPower["Video Type"].isin(["4K-VP9", "4K-AV1", "FHD-AV1", "FHD-H264", "FHD-VP9"])]).groupby(['Video Type']).mean().reset_index()

    # Now use the filtered columns to create the bar chart
    fig = px.bar(barDf, x='Video Type', y=['Efficiency Cluster', 'Performance Cluster', 'DRAM', 'GPU', 'Other'], template='plotly_dark', orientation='v', hover_name = 'Video Type',
    width = 700, height = 400, barmode = 'group', 
    # color_discrete_sequence = px.colors.qualitative.G10,
    # color_discrete_sequence=px.colors.qualitative.Set1,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0"
    },
    labels={"value": "Power Consumption (mW)"}, 
    category_orders={"Video Type": ["4K-VP9", "4K-AV1",  "FHD-AV1", "FHD-H264", "FHD-VP9"]})

    fig.update_yaxes(title_font = dict(size=12), title_font_color = "#707070", color="#707070",  tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424') #, range=[0, 1100])
    fig.update_xaxes(zeroline = True, showgrid=False, color="#FFF", title_font_color = "#707070", tickfont = dict(size = 11), title_text='')
    fig.update_traces(texttemplate='%{y:.0f}', textfont= dict(size=8), width=[0.11, 0.11, 0.11, 0.11, 0.11])
    fig.update_layout( autosize = True, hovermode=False, legend_title_text='',
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Average Power Consumption</b> <br> <sup> Apple Mac Mini M1 | VLC 3.0.12.1 (local files) | MacOS 11.2.2 </sup>",
            'y':0.93,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 30, b = 0, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    texts = [barDf['Efficiency Cluster'], barDf['Performance Cluster'], barDf['DRAM'], barDf['GPU'], barDf['Other']]
    for i, t in enumerate(texts):
        fig.data[i].text = t
        fig.data[i].textposition = 'outside'

    # fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    # fig.update_layout(uniformtext_minsize=7, uniformtext_mode='hide')

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.12, y=1.12,
            sizex=0.145, sizey=0.145,
            xanchor="left", yanchor="bottom"
        )
    )

    # Update just the layout properites with relatout method e.g. barmode
    # fig.update_layout(
    #     updatemenus=[
    #         dict(
    #             type="buttons",
    #             buttons=[
    #                 dict(label="Grouped",
    #                     method="relayout",
    #                     args = [{"barmode": "group"} ]),
    #                 dict(label="Stacked",
    #                     method="relayout",
    #                     args = [{"barmode": "stack"}, {"autosize": "True"} ])
    #             ]
    #         )
    #     ]
    # )

    # TODO: Figure out the fix for https://github.com/plotly/plotly.py/issues/3120 
    # Update the Layout + Trace properties
    # fig.update_layout(
    #     updatemenus=[
    #         dict(
    #             type="dropdown",
    #             # direction="right",
    #             active=0,
    #             x=1.035,
    #             y=1.27,
    #             showactive = True,
    #             buttons=list([
    #                 dict(label="Grouped",
    #                     method="update",
    #                     args=[{"width": [0.11]},
    #                         {"barmode": "group"}]),
    #                 dict(label="Stacked",
    #                     method="update",
    #                     args=[{"width": [0.6]},
    #                         {"barmode": "stack"}])
    #             ]),
    #             bgcolor = "#222",
    #             bordercolor = "#FFF",
    #             borderwidth = 0.5
    #         )
    #     ])

    # fig.add_annotation(text="Bar Mode:",
    # xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
    # x=0.89, y=1.25, showarrow=False, opacity=0.8, font=dict(size=13))

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=0.99, y=0.86, showarrow=False,  font=dict(size=14, color='#707070'))

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-power-average.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-power-average.svg")

    # HORIZONTAL BAR CHART FOR Total Average
    barDf = (dfPower.loc[dfPower["Video Type"].isin(["4K-VP9", "4K-AV1", "FHD-AV1", "FHD-H264", "FHD-VP9"])]).groupby(['Video Type']).mean().reset_index()
    fig = px.bar(barDf, y='Video Type', x=['Package'], template='plotly_dark', orientation='h', hover_name = 'Video Type',  width = 700, height = 250, #barmode = 'group', 
    # color_discrete_sequence=px.colors.sequential.Blugrn, 
    # color_discrete_sequence=px.colors.qualitative.Set1,
    color_discrete_map={"Package": "#57FFBC"},
    labels={"value": "Power Consumption (mW)"}, 
    category_orders={"Video Type": ["4K-VP9", "4K-AV1",  "FHD-AV1", "FHD-VP9", "FHD-H264"]})

    fig.update_xaxes(zeroline = True, title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424')
    fig.update_yaxes(zeroline = True, showgrid=False, color="#FFF", title_font_color = "#707070", tickfont = dict(size = 11), title_text='')
    fig.update_traces(hovertemplate='%{x:.0f} (mW)', texttemplate='%{x:.0f} mW', textfont= dict(size=11))
    fig.update_layout( autosize = True, hovermode=False, legend_title_text='',
        showlegend = False, font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Average Power Consumption</b> <br> <sup> Apple Mac Mini M1 | VLC 3.0.12.1 (local files) | MacOS 11.2.2 </sup>",
            'y':0.90,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 30, b = 15, t = 60),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#181F26',
        paper_bgcolor ='#181F26'
    )

    texts = [barDf['Package']]
    for i, t in enumerate(texts):
        fig.data[i].text = t
        fig.data[i].textposition = 'inside'

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=0.99, y=0.17, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.165, y=1.099,
            sizex=0.29, sizey=0.29,
            xanchor="left", yanchor="bottom"
        )
    )

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-power-average-total.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-power-average-total.svg")


    # Figure for CPU, GPU Frequency over time
    fig = px.line(dfFrequency.loc[dfFrequency["Video Type"].isin(["4K-VP9", "4K-AV1", "FHD-AV1", "FHD-H264", "FHD-VP9"])], x='time', y=['Efficiency Cluster', 'Performance Cluster', 'GPU'], template='plotly_dark', 
    width = 700, height = 350, facet_col='Video Type', line_shape= "spline", render_mode = "svg",  facet_col_wrap = 5,
    # color_discrete_sequence = px.colors.qualitative.G10,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Frequency (MHz)", "time": "Time (s)"},
    category_orders={"Video Type": ["4K-VP9", "4K-AV1", "FHD-AV1", "FHD-H264", "FHD-VP9"]})
    
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(family="SF Pro Display, Roboto, Droid Sans, Arial", size=11)
    
    fig.update_yaxes(type='linear', title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424')
    fig.update_xaxes(showgrid=False, title_font = dict(size=10), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9))
    fig.update_traces(hovertemplate='%{y} MHz', line_smoothing = 1.3)
    fig.update_layout(legend_title_text='', autosize = True, hovermode="x", 
        legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Frequency over Time</b> <br> <sup> Apple Mac Mini M1 | VLC 3.0.12.1 (local files) | MacOS 11.2.2 </sup>",
            'y':0.92,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 50, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=1, y=0.83, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.125, y=1.19,
            sizex=0.22, sizey=0.22,
            xanchor="left", yanchor="bottom"
        )
    )

    fig.write_html("outputs/plotly-frequency.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-frequency.svg")

   # BAR CHART FOR Averages by component
    barDf = (dfFrequency.loc[dfFrequency["Video Type"].isin(["4K-VP9", "4K-AV1", "FHD-AV1", "FHD-H264", "FHD-VP9"])]).groupby(['Video Type']).mean().reset_index()
    fig = px.bar(barDf, x='Video Type', y=['Efficiency Cluster', 'Performance Cluster', 'GPU'], template='plotly_dark', orientation='v', hover_name = 'Video Type',
    width = 700, height = 350, barmode = 'group', 
    # color_discrete_sequence=px.colors.sequential.Blugrn,
    # color_discrete_sequence=px.colors.qualitative.Set1,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Frequency (MHz)"}, 
    category_orders={"Video Type": ["4K-VP9", "4K-AV1",  "FHD-AV1", "FHD-H264", "FHD-VP9"]})

    fig.update_yaxes(title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424', range=[0, 1650])
    fig.update_xaxes(zeroline = True, showgrid=False, color="#FFF", title_font_color = "#707070", tickfont = dict(size = 11), title_text='')
    fig.update_traces(hovertemplate='%{y:.0f} (Hz)', texttemplate='%{y:.0f}', textfont= dict(size=8), width=[0.15, 0.15, 0.15, 0.15, 0.15])
    fig.update_layout( autosize = True, hovermode=False, legend_title_text='',
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Average Frequency</b> <br> <sup> Apple Mac Mini M1 | VLC 3.0.12.1 (local files) | MacOS 11.2.2 </sup>",
            'y':0.92,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 30, b = 0, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    texts = [barDf['Efficiency Cluster'], barDf['Performance Cluster'], barDf['GPU']]
    for i, t in enumerate(texts):
        fig.data[i].text = t
        fig.data[i].textposition = 'outside'

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=0.99, y=0.96, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.12, y=1.15,
            sizex=0.18, sizey=0.18,
            xanchor="left", yanchor="bottom"
        )
    )

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-frequency-average.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-frequency-average.svg")

    # Figure for CPU, GPU Usage over time
    fig = px.line(dfUsage.loc[dfUsage["Video Type"].isin(["4K-VP9", "4K-AV1", "FHD-AV1", "FHD-H264", "FHD-VP9"])], x='time', y=['Efficiency Cluster', 'Performance Cluster', 'GPU'], template='plotly_dark', 
    width = 700, height = 350, facet_col='Video Type', line_shape= "spline", render_mode = "svg",  facet_col_wrap = 5,
    # color_discrete_sequence = px.colors.qualitative.G10,
    # color_discrete_sequence= px.colors.sequential.Burgyl,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Usage (%)", "time": "Time (s)"},
    category_orders={"Video Type": ["4K-VP9", "4K-AV1", "FHD-AV1", "FHD-H264", "FHD-VP9"]})
    
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(family="SF Pro Display, Roboto, Droid Sans, Arial", size=11)
    
    fig.update_yaxes(type='linear', title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424', ticksuffix = "%")
    fig.update_xaxes(showgrid=False, title_font = dict(size=10), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9))
    fig.update_traces(hovertemplate='%{y:.0f} %', line_smoothing = 1.3)
    fig.update_layout(legend_title_text='', autosize = True, hovermode="x", 
        legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Usage over Time</b> <br> <sup> Apple Mac Mini M1 | VLC 3.0.12.1 (local files) | MacOS 11.2.2 </sup>",
            'y':0.92,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 50, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=1, y=0.9, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.125, y=1.19,
            sizex=0.22, sizey=0.22,
            xanchor="left", yanchor="bottom"
        )
    )

    fig.write_html("outputs/plotly-usage.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-usage.svg")

 # BAR CHART FOR Averages by component
    barDf = (dfUsage.loc[dfUsage["Video Type"].isin(["4K-VP9", "4K-AV1", "FHD-AV1", "FHD-H264", "FHD-VP9"])]).groupby(['Video Type']).mean().reset_index()
    fig = px.bar(barDf, x='Video Type', y=['Efficiency Cluster', 'Performance Cluster', 'GPU'], template='plotly_dark', orientation='v', hover_name = 'Video Type',
    width = 700, height = 350, barmode = 'group', 
    # color_discrete_sequence=px.colors.sequential.Blugrn,
    # color_discrete_sequence=px.colors.qualitative.Set1,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Usage (%)"}, 
    category_orders={"Video Type": ["4K-VP9", "4K-AV1",  "FHD-AV1", "FHD-H264", "FHD-VP9"]})

    fig.update_yaxes(title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424', range=[0, 29], ticksuffix = "%")
    fig.update_xaxes(zeroline = True, showgrid=False, color="#FFF", title_font_color = "#707070", tickfont = dict(size = 11), title_text='')
    fig.update_traces(hovertemplate='%{y:.0f} (%)', texttemplate='%{y:.0f} %', textfont= dict(size=8), width=[0.15, 0.15, 0.15, 0.15, 0.15])
    fig.update_layout( autosize = True, hovermode=False, legend_title_text='',
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Average Usage</b> <br> <sup> Apple Mac Mini M1 | VLC 3.0.12.1 (local files) | MacOS 11.2.2 </sup>",
            'y':0.92,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 30, b = 0, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    texts = [barDf['Efficiency Cluster'], barDf['Performance Cluster'], barDf['GPU']]
    for i, t in enumerate(texts):
        fig.data[i].text = t
        fig.data[i].textposition = 'outside'

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=0.99, y=0.96, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.12, y=1.15,
            sizex=0.18, sizey=0.18,
            xanchor="left", yanchor="bottom"
        )
    )

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-usage-average.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-usage-average.svg")

def buildYouTubeCharts(dfPower, dfFrequency, dfUsage, config, kLogo):
    dfPower["Video Type"].replace({'4K-VP9':'VLC-SW', "Chrome-HW-YT-4K":"Chrome-HW", "Safari-HW-YT-4K":"Safari-HW"}, inplace=True)
    dfFrequency["Video Type"].replace({'4K-VP9':'VLC-SW', "Chrome-HW-YT-4K":"Chrome-HW", "Safari-HW-YT-4K":"Safari-HW"}, inplace=True)
    dfUsage["Video Type"].replace({'4K-VP9':'VLC-SW', "Chrome-HW-YT-4K":"Chrome-HW", "Safari-HW-YT-4K":"Safari-HW"}, inplace=True)

    # Figure for Package Power Over Time
    fig = px.area(dfPower.loc[dfPower["Video Type"].isin(["VLC-SW", "Safari-HW", "Chrome-HW", "Chrome-SW"])], x='time', y=['Package'], template='plotly_dark', 
    width = 700, height = 350, facet_col='Video Type', line_shape= "spline", facet_col_wrap = 5,
    labels={"value": "Power Consumption (mW)", "time": "Time (s)"}, color_discrete_map={"Package": "#57FFBC"},
    category_orders={"Video Type": ["VLC-SW", "Safari-HW", "Chrome-HW", "Chrome-SW"]})
    
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(family="SF Pro Display, Roboto, Droid Sans, Arial", size=11)
    
    fig.update_yaxes(type='linear', title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424')
    fig.update_xaxes(showgrid=False, title_font = dict(size=10), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9))
    fig.update_traces(hovertemplate='%{y} (mW)', line_smoothing = 1.3)
    fig.update_layout(autosize = True, hovermode="x", 
        showlegend = False, font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Total Package Power Consumption over Time</b> <br> <sup> Apple Mac Mini M1 | YouTube VP9 4K SDR | MacOS 11.2.2 </sup>",
            'y':0.92,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 50, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=1.05, y=1.3, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.12, y=1.17,
            sizex=0.2, sizey=0.2,
            xanchor="left", yanchor="bottom"
        )
    )

    fig.write_html("outputs/plotly-power-package-browser.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-power-package-browser.svg")

    # Figure for Total Power Over Time
    fig = px.line(dfPower.loc[dfPower["Video Type"].isin(["VLC-SW", "Safari-HW", "Chrome-HW", "Chrome-SW"])], x='time', y=['Efficiency Cluster', 'Performance Cluster', 'DRAM', 'GPU', 'Other'], template='plotly_dark', 
    width = 700, height = 900, facet_row='Video Type', line_shape= "spline", render_mode = "svg",
    # color_discrete_sequence = px.colors.qualitative.G10,
    # color_discrete_sequence=px.colors.sequential.YlOrRd,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Power Consumption (mW)", "time": "Time (s)"}, 
    category_orders={"Video Type": ["VLC-SW", "Chrome-SW", "Safari-HW", "Chrome-HW"]})

    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    for annotation in fig['layout']['annotations']: 
        # print(annotation)
        annotation['textangle'] = 0
        annotation['xanchor'] = 'right'
        annotation['x'] = annotation['x'] - 0.002
        annotation['y'] = annotation['y'] + 0.038
        annotation['font'] = dict(family="SF Pro Display, Roboto, Droid Sans, Arial", size=13)

    fig.update_yaxes(type='linear', title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424')
    fig.update_xaxes(showgrid=False, color="#707070", title_font_color = "#707070", tickfont = dict(size = 9))
    # fig.update_traces(hovertemplate='%{y} (mW)', line_smoothing = 1.3)
    fig.update_traces(hovertemplate='%{y} (mW)')
    fig.update_layout(legend_title_text='', autosize = True, hovermode="x", 
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Power Consumption over Time</b> <br> <sup> Apple Mac Mini M1 | YouTube VP9 4K SDR | MacOS 11.2.2 </sup>",
            'y':0.97,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 30, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'left', yanchor = 'top', 
        x=0.85, y=0.75, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.12, y=1.04,
            sizex=0.067, sizey=0.067,
            xanchor="left", yanchor="bottom"
        )
    )

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-power-total-browser.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-power-total-browser.svg")

     # BAR CHART FOR Averages by component
    barDf = (dfPower.loc[dfPower["Video Type"].isin(["VLC-SW", "Safari-HW", "Chrome-HW", "Chrome-SW"])]).groupby(['Video Type']).mean().reset_index()
    fig = px.bar(barDf, x='Video Type', y=['Efficiency Cluster', 'Performance Cluster', 'DRAM', 'GPU', 'Other'], template='plotly_dark', orientation='v', hover_name = 'Video Type',
    width = 700, height = 400, barmode = 'group', 
    # color_discrete_sequence=px.colors.sequential.Blugrn,
    # color_discrete_sequence=px.colors.qualitative.Set1,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Power Consumption (mW)"}, 
    category_orders={"Video Type": ["VLC-SW", "Safari-HW", "Chrome-HW", "Chrome-SW"]})

    fig.update_yaxes(title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424', range=[0, 1100])
    fig.update_xaxes(zeroline = True, showgrid=False, color="#FFF", title_font_color = "#707070", tickfont = dict(size = 11), title_text='')
    fig.update_traces(hovertemplate='%{y:.0f} (mW)', texttemplate='%{y:.0f}', textfont= dict(size=8), width=[0.11, 0.11, 0.11, 0.11, 0.11])
    fig.update_layout( autosize = True, hovermode=False, legend_title_text='',
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Average Power Consumption</b> <br> <sup> Apple Mac Mini M1 | YouTube VP9 4K SDR | MacOS 11.2.2 </sup>",
            'y':0.93,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 30, b = 0, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    texts = [barDf['Efficiency Cluster'], barDf['Performance Cluster'], barDf['DRAM'], barDf['GPU'], barDf['Other']]
    for i, t in enumerate(texts):
        fig.data[i].text = t
        fig.data[i].textposition = 'outside'

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=0.99, y=0.86, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.12, y=1.12,
            sizex=0.145, sizey=0.145,
            xanchor="left", yanchor="bottom"
        )
    )

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-power-average-browser.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-power-average-browser.svg")

    # HORIZONTAL BAR CHART FOR Total Average
    barDf = (dfPower.loc[dfPower["Video Type"].isin(["VLC-SW", "Safari-HW", "Chrome-HW", "Chrome-SW"])]).groupby(['Video Type']).mean().reset_index()
    fig = px.bar(barDf, y='Video Type', x=['Package'], template='plotly_dark', orientation='h', hover_name = 'Video Type',  width = 700, height = 250, #barmode = 'group', 
    # color_discrete_sequence=px.colors.sequential.Blugrn, 
    # color_discrete_sequence=px.colors.qualitative.Set1,
    color_discrete_map={"Package": "#57FFBC"},
    # color_discrete_map={
    #     "Efficiency Cluster": "#9D788C",
    #     "Performance Cluster": "#2A9D8F",
    #     "DRAM": "#E9C46A",
    #     "GPU": "#F4A261",
    #     # "Other": "rgb(95, 70, 144)"
    #     "Other": "#E76F51"
    # },
    labels={"value": "Power Consumption (mW)"}, 
    category_orders={"Video Type": ["Safari-HW", "Chrome-HW", "Chrome-SW", "VLC-SW"]})

    fig.update_xaxes(zeroline = True, title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424')
    fig.update_yaxes(zeroline = True, showgrid=False, color="#FFF", title_font_color = "#707070", tickfont = dict(size = 11), title_text='')
    fig.update_traces(hovertemplate='%{x:.0f} (mW)', texttemplate='%{x:.0f} mW', textfont= dict(size=11))
    fig.update_layout( autosize = True, hovermode=False, legend_title_text='',
        showlegend = False, font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Average Power Consumption</b> <br> <sup> Apple Mac Mini M1 | YouTube VP9 4K SDR | MacOS 11.2.2 </sup>",
            'y':0.90,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 30, b = 15, t = 60),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    texts = [barDf['Package']]
    for i, t in enumerate(texts):
        print('i = ', i,'t= ' ,t)
        fig.data[i].text = t
        fig.data[i].textposition = 'inside'

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=0.99, y=1, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.18, y=1.099,
            sizex=0.29, sizey=0.29,
            xanchor="left", yanchor="bottom"
        )
    )

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-power-average-total-browser.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-power-average-total-browser.svg")


    # Figure for CPU, GPU Frequency over time
    fig = px.line(dfFrequency.loc[dfFrequency["Video Type"].isin(["VLC-SW", "Safari-HW", "Chrome-HW", "Chrome-SW"])], x='time', y=['Efficiency Cluster', 'Performance Cluster', 'GPU'], template='plotly_dark', 
    width = 700, height = 350, facet_col='Video Type', line_shape= "spline", render_mode = "svg",  facet_col_wrap = 5,
    # color_discrete_sequence = px.colors.qualitative.G10,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Frequency (MHz)", "time": "Time (s)"},
    category_orders={"Video Type": ["VLC-SW", "Safari-HW", "Chrome-HW", "Chrome-SW"]})
    
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(family="SF Pro Display, Roboto, Droid Sans, Arial", size=11)
    
    fig.update_yaxes(type='linear', title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424')
    fig.update_xaxes(showgrid=False, title_font = dict(size=10), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9))
    fig.update_traces(hovertemplate='%{y} MHz', line_smoothing = 1.3)
    fig.update_layout(legend_title_text='', autosize = True, hovermode="x", 
        legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Frequency over Time</b> <br> <sup> Apple Mac Mini M1 | YouTube VP9 4K SDR | MacOS 11.2.2 </sup>",
            'y':0.92,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 50, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=1.05, y=1.3, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.125, y=1.19,
            sizex=0.22, sizey=0.22,
            xanchor="left", yanchor="bottom"
        )
    )

    fig.write_html("outputs/plotly-frequency-browser.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-frequency-browser.svg")

   # Average Frequency
    barDf = (dfFrequency.loc[dfFrequency["Video Type"].isin(["VLC-SW", "Safari-HW", "Chrome-HW", "Chrome-SW"])]).groupby(['Video Type']).mean().reset_index()
    fig = px.bar(barDf, x='Video Type', y=['Efficiency Cluster', 'Performance Cluster', 'GPU'], template='plotly_dark', orientation='v', hover_name = 'Video Type',
    width = 700, height = 350, barmode = 'group', 
    # color_discrete_sequence=px.colors.sequential.Blugrn,
    # color_discrete_sequence=px.colors.qualitative.Set1,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Frequency (MHz)"}, 
    category_orders={"Video Type": ["VLC-SW", "Safari-HW", "Chrome-HW", "Chrome-SW"]})

    fig.update_yaxes(title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424', range=[0, 1650])
    fig.update_xaxes(zeroline = True, showgrid=False, color="#FFF", title_font_color = "#707070", tickfont = dict(size = 11), title_text='')
    fig.update_traces(hovertemplate='%{y:.0f} (Hz)', texttemplate='%{y:.0f}', textfont= dict(size=8), width=[0.15, 0.15, 0.15, 0.15, 0.15])
    fig.update_layout( autosize = True, hovermode=False, legend_title_text='',
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Average Frequency</b> <br> <sup> Apple Mac Mini M1 | YouTube VP9 4K SDR | MacOS 11.2.2 </sup>",
            'y':0.92,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 30, b = 0, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    texts = [barDf['Efficiency Cluster'], barDf['Performance Cluster'], barDf['GPU']]
    for i, t in enumerate(texts):
        fig.data[i].text = t
        fig.data[i].textposition = 'outside'

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=0.99, y=1.25, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.12, y=1.15,
            sizex=0.18, sizey=0.18,
            xanchor="left", yanchor="bottom"
        )
    )

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-frequency-average-browser.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-frequency-average-browser.svg")

    # Figure for CPU, GPU Usage over time
    fig = px.line(dfUsage.loc[dfUsage["Video Type"].isin(["VLC-SW", "Safari-HW", "Chrome-HW", "Chrome-SW"])], x='time', y=['Efficiency Cluster', 'Performance Cluster', 'GPU'], template='plotly_dark', 
    width = 700, height = 350, facet_col='Video Type', line_shape= "spline", render_mode = "svg",  facet_col_wrap = 5,
    # color_discrete_sequence = px.colors.qualitative.G10,
    # color_discrete_sequence= px.colors.sequential.Burgyl,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Usage (%)", "time": "Time (s)"},
    category_orders={"Video Type": ["VLC-SW", "Safari-HW", "Chrome-HW", "Chrome-SW"]})
    
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(family="SF Pro Display, Roboto, Droid Sans, Arial", size=11)
    
    fig.update_yaxes(type='linear', title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424', ticksuffix = "%")
    fig.update_xaxes(showgrid=False, title_font = dict(size=10), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9))
    fig.update_traces(hovertemplate='%{y:.0f} %', line_smoothing = 1.3)
    fig.update_layout(legend_title_text='', autosize = True, hovermode="x", 
        legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Usage over Time</b> <br> <sup> Apple Mac Mini M1 | YouTube VP9 4K SDR | MacOS 11.2.2 </sup>",
            'y':0.92,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 50, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=1.05, y=1.3, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.125, y=1.19,
            sizex=0.22, sizey=0.22,
            xanchor="left", yanchor="bottom"
        )
    )

    fig.write_html("outputs/plotly-usage-browser.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-usage-browser.svg")

 # BAR CHART FOR Averages by component
    barDf = (dfUsage.loc[dfUsage["Video Type"].isin(["VLC-SW", "Safari-HW", "Chrome-HW", "Chrome-SW"])]).groupby(['Video Type']).mean().reset_index()
    fig = px.bar(barDf, x='Video Type', y=['Efficiency Cluster', 'Performance Cluster', 'GPU'], template='plotly_dark', orientation='v', hover_name = 'Video Type',
    width = 700, height = 350, barmode = 'group', 
    # color_discrete_sequence=px.colors.sequential.Blugrn,
    # color_discrete_sequence=px.colors.qualitative.Set1,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Usage (%)"}, 
    category_orders={"Video Type": ["VLC-SW", "Safari-HW", "Chrome-HW", "Chrome-SW"]})

    fig.update_yaxes(title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424', range=[0, 32], ticksuffix = "%")
    fig.update_xaxes(zeroline = True, showgrid=False, color="#FFF", title_font_color = "#707070", tickfont = dict(size = 11), title_text='')
    fig.update_traces(hovertemplate='%{y:.0f} (%)', texttemplate='%{y:.0f} %', textfont= dict(size=8), width=[0.15, 0.15, 0.15, 0.15, 0.15])
    fig.update_layout( autosize = True, hovermode=False, legend_title_text='',
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Average Usage</b> <br> <sup> Apple Mac Mini M1 | YouTube VP9 4K SDR | MacOS 11.2.2 </sup>",
            'y':0.92,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 30, b = 0, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    texts = [barDf['Efficiency Cluster'], barDf['Performance Cluster'], barDf['GPU']]
    for i, t in enumerate(texts):
        fig.data[i].text = t
        fig.data[i].textposition = 'outside'

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=1, y=1.25, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.12, y=1.15,
            sizex=0.18, sizey=0.18,
            xanchor="left", yanchor="bottom"
        )
    )

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-usage-average-browser.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-usage-average-browser.svg")

def buildNetflixCharts(dfPower, dfFrequency, dfUsage, config, kLogo):
    dfPower["Video Type"].replace({"Safari-Netflix-1080p":"Safari (H.265 1080p)", "Chrome-Netflix-720p":"Chrome (VP9 720p)"}, inplace=True)
    dfFrequency["Video Type"].replace({"Safari-Netflix-1080p":"Safari (H.265 1080p)", "Chrome-Netflix-720p":"Chrome (VP9 720p)"}, inplace=True)
    dfUsage["Video Type"].replace({"Safari-Netflix-1080p":"Safari (H.265 1080p)", "Chrome-Netflix-720p":"Chrome (VP9 720p)"}, inplace=True)
    
    # Figure for Package Power Over Time
    fig = px.line(dfPower.loc[dfPower["Video Type"].isin(["Safari (H.265 1080p)", "Chrome (VP9 720p)"])], x='time', y=['Package'], template='plotly_dark', 
    width = 700, height = 350, 
    color='Video Type', line_shape= "spline", render_mode = "svg", 
    # color_discrete_sequence = px.colors.qualitative.G10,
    color_discrete_map={
        "Safari (H.265 1080p)": "#19C0FC",
        "Chrome (VP9 720p)": "#FAD108"
    },
    labels={"value": "Power Consumption (mW)", "time": "Time (s)"})
    
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(family="SF Pro Display, Roboto, Droid Sans, Arial", size=11)
    
    fig.update_yaxes(type='linear', title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424')
    fig.update_xaxes(showgrid=False, title_font = dict(size=10), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9))
    fig.update_traces(hovertemplate='%{y} (mW)', line_smoothing = 1.3)
    fig.update_layout(autosize = True, hovermode="x", legend_title_text='',
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="center", x=0.5), font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Total Package Power Consumption over Time</b> <br> <sup> Apple Mac Mini M1 | Netflix Queen's Gambit | MacOS 11.2.2 </sup>",
            'y':0.92,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 50, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=1.05, y=1.1, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.125, y=1.18,
            sizex=0.21, sizey=0.21,
            xanchor="left", yanchor="bottom"
        )
    )

    fig.write_html("outputs/plotly-power-package-netflix.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-power-package-netflix.svg")

    # Figure for Total Power Over Time
    fig = px.line(dfPower.loc[dfPower["Video Type"].isin(['Safari (H.265 1080p)', "Chrome (VP9 720p)"])], x='time', y=['Efficiency Cluster', 'Performance Cluster', 'DRAM', 'GPU', 'Other'], template='plotly_dark', 
    width = 700, height = 500, facet_row='Video Type', line_shape= "spline", render_mode = "svg",
    # color_discrete_sequence = px.colors.qualitative.G10,
    # color_discrete_sequence=px.colors.sequential.YlOrRd,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Power Consumption (mW)", "time": "Time (s)"}, 
    category_orders={"Video Type": ['Safari (H.265 1080p)', "Chrome (VP9 720p)"]})

    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    for annotation in fig['layout']['annotations']: 
        # print(annotation)
        annotation['textangle'] = 0
        annotation['xanchor'] = 'right'
        annotation['x'] = annotation['x'] - 0.002
        annotation['y'] = annotation['y'] + 0.088
        annotation['font'] = dict(family="SF Pro Display, Roboto, Droid Sans, Arial", size=13)

    fig.update_yaxes(type='linear', title_font = dict(size=10), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424')
    fig.update_xaxes(showgrid=False, title_font = dict(size=11), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9))
    # fig.update_traces(hovertemplate='%{y} (mW)', line_smoothing = 1.3)
    fig.update_traces(hovertemplate='%{y} (mW)')
    fig.update_layout(legend_title_text='', autosize = True, hovermode="x", 
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Power Consumption over Time</b> <br> <sup> Apple Mac Mini M1 | Netflix Queen's Gambit | MacOS 11.2.2 </sup>",
            'y':0.94,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 30, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'left', yanchor = 'top', 
        x=0.8, y=-0.1, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.12, y=1.09,
            sizex=0.12, sizey=0.12,
            xanchor="left", yanchor="bottom"
        )
    )

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-power-total-netflix.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-power-total-netflix.svg")

   # BAR CHART FOR Averages by component
    barDf = (dfPower.loc[dfPower["Video Type"].isin(["Safari (H.265 1080p)", "Chrome (VP9 720p)"])]).groupby(['Video Type']).mean().reset_index()
    fig = px.bar(barDf, x='Video Type', y=['Efficiency Cluster', 'Performance Cluster', 'DRAM', 'GPU', 'Other'], template='plotly_dark', orientation='v', hover_name = 'Video Type',
    width = 700, height = 400, barmode = 'group', 
    # color_discrete_sequence=px.colors.sequential.Blugrn,
    # color_discrete_sequence=px.colors.qualitative.Set1,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Power Consumption (mW)"}, 
    category_orders={"Video Type": ["Safari (H.265 1080p)", "Chrome (VP9 720p)"]})

    fig.update_yaxes(title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424', range=[0, 65])
    fig.update_xaxes(zeroline = True, showgrid=False, color="#FFF", title_font_color = "#707070", tickfont = dict(size = 11), title_text='')
    fig.update_traces(hovertemplate='%{y:.0f} (mW)', texttemplate='%{y:.0f}', textfont= dict(size=8), width=[0.11, 0.11, 0.11, 0.11, 0.11])
    fig.update_layout( autosize = True, hovermode=False, legend_title_text='',
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Average Power Consumption</b> <br> <sup> Apple Mac Mini M1 | Netflix Queen's Gambit | MacOS 11.2.2 </sup>",
            'y':0.93,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 30, b = 0, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    texts = [barDf['Efficiency Cluster'], barDf['Performance Cluster'], barDf['DRAM'], barDf['GPU'], barDf['Other']]
    for i, t in enumerate(texts):
        fig.data[i].text = t
        fig.data[i].textposition = 'outside'

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=0.99, y=0.9, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.12, y=1.12,
            sizex=0.145, sizey=0.145,
            xanchor="left", yanchor="bottom"
        )
    )

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-power-average-netflix.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-power-average-netflix.svg")

    # HORIZONTAL BAR CHART FOR Total Average
    barDf = (dfPower.loc[dfPower["Video Type"].isin(["Safari (H.265 1080p)", "Chrome (VP9 720p)"])]).groupby(['Video Type']).mean().reset_index()
    fig = px.bar(barDf, y='Video Type', x=['Package'], template='plotly_dark', orientation='h', hover_name = 'Video Type',  width = 700, height = 200, #barmode = 'group', 
    # color_discrete_sequence=px.colors.sequential.Blugrn, 
    # color_discrete_sequence=px.colors.qualitative.Set1,
    color_discrete_map={"Package": "#57FFBC"},
    # color_discrete_map={
    #     "Efficiency Cluster": "#9D788C",
    #     "Performance Cluster": "#2A9D8F",
    #     "DRAM": "#E9C46A",
    #     "GPU": "#F4A261",
    #     # "Other": "rgb(95, 70, 144)"
    #     "Other": "#E76F51"
    # },
    labels={"value": "Power Consumption (mW)"}, 
    category_orders={"Video Type": ["Safari-HW", "Chrome-HW", "Chrome-SW", "VLC-SW"]})

    fig.update_xaxes(zeroline = True, title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424')
    fig.update_yaxes(zeroline = True, showgrid=False, color="#FFF", title_font_color = "#707070", tickfont = dict(size = 11), title_text='')
    fig.update_traces(hovertemplate='%{x:.0f} (mW)', texttemplate='%{x:.0f} mW', textfont= dict(size=11))
    fig.update_layout( autosize = True, hovermode=False, legend_title_text='',
        showlegend = False, font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Average Power Consumption</b> <br> <sup> Apple Mac Mini M1 | Netflix Queen's Gambit | MacOS 11.2.2 </sup>",
            'y':0.87,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 30, b = 15, t = 60),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    texts = [barDf['Package']]
    for i, t in enumerate(texts):
        print('i = ', i,'t= ' ,t)
        fig.data[i].text = t
        fig.data[i].textposition = 'inside'

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=1.02, y=1.5, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.27, y=1.16,
            sizex=0.49, sizey=0.49,
            xanchor="left", yanchor="bottom"
        )
    )

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-power-average-total-netflix.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-power-average-total-netflix.svg")


    # Figure for CPU, GPU Frequency over time
    fig = px.line(dfFrequency.loc[dfFrequency["Video Type"].isin(["Safari (H.265 1080p)", "Chrome (VP9 720p)"])], x='time', y=['Efficiency Cluster', 'Performance Cluster', 'GPU'], template='plotly_dark', 
    width = 700, height = 350, facet_col='Video Type', line_shape= "spline", render_mode = "svg",  facet_col_wrap = 5,
    # color_discrete_sequence = px.colors.qualitative.G10,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Frequency (MHz)", "time": "Time (s)"},
    category_orders={"Video Type": ["Safari (H.265 1080p)", "Chrome (VP9 720p)"]})
    
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(family="SF Pro Display, Roboto, Droid Sans, Arial", size=11)
    
    fig.update_yaxes(type='linear', title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424')
    fig.update_xaxes(showgrid=False, title_font = dict(size=10), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9))
    fig.update_traces(hovertemplate='%{y} MHz', line_smoothing = 1.3)
    fig.update_layout(legend_title_text='', autosize = True, hovermode="x", 
        legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Frequency over Time</b> <br> <sup> Apple Mac Mini M1 | Netflix Queen's Gambit | MacOS 11.2.2 </sup>",
            'y':0.92,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 50, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=1.05, y=1.3, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.125, y=1.19,
            sizex=0.22, sizey=0.22,
            xanchor="left", yanchor="bottom"
        )
    )

    fig.write_html("outputs/plotly-frequency-netflix.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-frequency-netflix.svg")

   # Average Frequency
    barDf = (dfFrequency.loc[dfFrequency["Video Type"].isin(["Safari (H.265 1080p)", "Chrome (VP9 720p)"])]).groupby(['Video Type']).mean().reset_index()
    fig = px.bar(barDf, x='Video Type', y=['Efficiency Cluster', 'Performance Cluster', 'GPU'], template='plotly_dark', orientation='v', hover_name = 'Video Type',
    width = 700, height = 350, barmode = 'group', 
    # color_discrete_sequence=px.colors.sequential.Blugrn,
    # color_discrete_sequence=px.colors.qualitative.Set1,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Frequency (MHz)"}, 
    category_orders={"Video Type": ["Safari (H.265 1080p)", "Chrome (VP9 720p)"]})

    fig.update_yaxes(title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424', range=[0, 1250])
    fig.update_xaxes(zeroline = True, showgrid=False, color="#FFF", title_font_color = "#707070", tickfont = dict(size = 11), title_text='')
    fig.update_traces(hovertemplate='%{y:.0f} (Hz)', texttemplate='%{y:.0f}', textfont= dict(size=8), width=[0.15, 0.15, 0.15, 0.15, 0.15])
    fig.update_layout( autosize = True, hovermode=False, legend_title_text='',
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Average Frequency</b> <br> <sup> Apple Mac Mini M1 | Netflix Queen's Gambit | MacOS 11.2.2 </sup>",
            'y':0.92,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 30, b = 0, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    texts = [barDf['Efficiency Cluster'], barDf['Performance Cluster'], barDf['GPU']]
    for i, t in enumerate(texts):
        fig.data[i].text = t
        fig.data[i].textposition = 'outside'

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=0.99, y=1.25, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.12, y=1.15,
            sizex=0.18, sizey=0.18,
            xanchor="left", yanchor="bottom"
        )
    )

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-frequency-average-netflix.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-frequency-average-netflix.svg")

    # Figure for CPU, GPU Usage over time
    fig = px.line(dfUsage.loc[dfUsage["Video Type"].isin(["Safari (H.265 1080p)", "Chrome (VP9 720p)"])], x='time', y=['Efficiency Cluster', 'Performance Cluster', 'GPU'], template='plotly_dark', 
    width = 700, height = 350, facet_col='Video Type', line_shape= "spline", render_mode = "svg",  facet_col_wrap = 5,
    # color_discrete_sequence = px.colors.qualitative.G10,
    # color_discrete_sequence= px.colors.sequential.Burgyl,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Usage (%)", "time": "Time (s)"},
    category_orders={"Video Type": ["Safari (H.265 1080p)", "Chrome (VP9 720p)"]})
    
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(family="SF Pro Display, Roboto, Droid Sans, Arial", size=11)
    
    fig.update_yaxes(type='linear', title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424', ticksuffix = "%")
    fig.update_xaxes(showgrid=False, title_font = dict(size=10), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9))
    fig.update_traces(hovertemplate='%{y:.0f} %', line_smoothing = 1.3)
    fig.update_layout(legend_title_text='', autosize = True, hovermode="x", 
        legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Usage over Time</b> <br> <sup> Apple Mac Mini M1 | Netflix Queen's Gambit | MacOS 11.2.2 </sup>",
            'y':0.92,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 50, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=1.05, y=1.3, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.125, y=1.19,
            sizex=0.22, sizey=0.22,
            xanchor="left", yanchor="bottom"
        )
    )

    fig.write_html("outputs/plotly-usage-netflix.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-usage-netflix.svg")

 # BAR CHART FOR Averages by component
    barDf = (dfUsage.loc[dfUsage["Video Type"].isin(["Safari (H.265 1080p)", "Chrome (VP9 720p)"])]).groupby(['Video Type']).mean().reset_index()
    fig = px.bar(barDf, x='Video Type', y=['Efficiency Cluster', 'Performance Cluster', 'GPU'], template='plotly_dark', orientation='v', hover_name = 'Video Type',
    width = 700, height = 350, barmode = 'group', 
    # color_discrete_sequence=px.colors.sequential.Blugrn,
    # color_discrete_sequence=px.colors.qualitative.Set1,
    color_discrete_map={
        "Efficiency Cluster": "#73A4FF",
        "Performance Cluster": "#FF715A",
        "DRAM": "#C590FF",
        "GPU": "#01F0B0",
        "Other": "#FEAF73"
    },
    labels={"value": "Usage (%)"}, 
    category_orders={"Video Type": ["Safari (H.265 1080p)", "Chrome (VP9 720p)"]})

    fig.update_yaxes(title_font = dict(size=12), color="#707070", title_font_color = "#707070", tickfont = dict(size = 9), gridcolor='#242424', zerolinecolor = '#242424', range=[0, 20], ticksuffix = "%")
    fig.update_xaxes(zeroline = True, showgrid=False, color="#FFF", title_font_color = "#707070", tickfont = dict(size = 11), title_text='')
    fig.update_traces(hovertemplate='%{y:.0f} (%)', texttemplate='%{y:.0f} %', textfont= dict(size=8), width=[0.15, 0.15, 0.15, 0.15, 0.15])
    fig.update_layout( autosize = True, hovermode=False, legend_title_text='',
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="center", x=0.5), 
        font = dict(family="SF Pro Display, Roboto, Droid Sans, Arial"),
        title={
            'text': "<b>Average Usage</b> <br> <sup> Apple Mac Mini M1 | Netflix Queen's Gambit | MacOS 11.2.2 </sup>",
            'y':0.92,
            'x':0.54,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18, color='#FFF')},
        margin = dict(r = 30, b = 0, t = 80),
        margin_pad = 10,
        modebar = dict(orientation = 'v'),
        plot_bgcolor='#191C1F',
        paper_bgcolor ='#191C1F'
    )

    texts = [barDf['Efficiency Cluster'], barDf['Performance Cluster'], barDf['GPU']]
    for i, t in enumerate(texts):
        fig.data[i].text = t
        fig.data[i].textposition = 'outside'

    fig.add_annotation(text="//singhkays.com",
        xref="paper", yref="paper", xanchor = 'right', yanchor = 'top', 
        x=1, y=1.25, showarrow=False,  font=dict(size=14, color='#707070'))

    fig.add_layout_image(
        dict(
            source=kLogo,
            xref="paper", yref="paper",
            x=-0.12, y=1.15,
            sizex=0.18, sizey=0.18,
            xanchor="left", yanchor="bottom"
        )
    )

    #fig.write_image("plotly-power.svg")
    fig.write_html("outputs/plotly-usage-average-netflix.html", include_plotlyjs="cdn", config = config)
    fig.write_image("outputs/plotly-usage-average-netflix.svg")

def outputExcel(dfPower, dfFrequency, dfUsage):
    # create excel writer object
    writer = pd.ExcelWriter('outputs/output.xlsx')

    # Write a different sheet for each dataframe
    dfPower.to_excel(writer, sheet_name = 'power', freeze_panes=(1,1), index = False) 
    dfFrequency.to_excel(writer, sheet_name = 'frequency', freeze_panes=(1,1), index = False) 
    dfUsage.to_excel(writer, sheet_name = 'usage', freeze_panes=(1,1), index = False) 

    print("Exporting Excel file...")
    writer.save()


def main():
    start_time = time.time()
    print("Starting at = ", time.ctime(start_time))
    directory_path = os.getcwd()

    # Current directory should have a folder named powermetric-logs which contains the output logs of powermetric runs
    powerLogsFolderName = "powermetric-logs"

    # Build the full path to the logs folder
    pathLogsFolder = directory_path + '/' + powerLogsFolderName + '/'

    # Get the list of all log files in the logs folder
    powerLogsList = os.listdir(pathLogsFolder)

    # Create local dataframes
    dfPower, dfFrequency, dfUsage = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Parse each log file
    for logsFile in powerLogsList:

        if not os.path.isfile(pathLogsFolder + logsFile): 
            print('File does not exist.')
        else:
            file = open(pathLogsFolder + logsFile, 'r', encoding="utf8", errors='ignore')
            content = file.read()
        
        if (logsFile.find('mp4') >= 0) or (logsFile.find('webm') >= 0):
            # Transform 4K-AV1.mp4.txt -> 4K-AV1 because that's what we want in the charts
            f_name = os.path.splitext(logsFile)[0]
            videoType = str.split(f_name, '.')[0]
        else:
            # Used for file paths like Safari-VP9-HW.txt i.e. without the video container (mp4, webm)
            videoType = os.path.splitext(logsFile)[0]

        # Parse the content and build Data Frames
        dfPowerTemp, dfFrequencyTemp, dfUsageTemp = regexParse(content, videoType)
        dfPower     = pd.concat([dfPower, dfPowerTemp], ignore_index=True)
        dfFrequency = pd.concat([dfFrequency, dfFrequencyTemp], ignore_index=True)
        dfUsage     = pd.concat([dfUsage, dfUsageTemp], ignore_index=True)

   # Common Plotly config parameter to be passed to each chart
    config = dict({
        'modeBarButtonsToRemove': ['toggleSpikelines', 'hoverClosestCartesian',  'hoverCompareCartesian', 'select2d', 'lasso2d'],
        'displaylogo': False
    })

    # Logo file to add to the charts
    kLogo = Image.open("favicon-97x98-white.png")

    # Build charts and output the Excel file
    buildVLCCharts(dfPower, dfFrequency, dfUsage, config, kLogo)
    buildYouTubeCharts(dfPower, dfFrequency, dfUsage, config, kLogo)
    buildNetflixCharts(dfPower, dfFrequency, dfUsage, config, kLogo)
    outputExcel(dfPower, dfFrequency, dfUsage)

    #print(dfPower)
    end_time = time.time()
    print("Ending at = ", time.ctime(end_time))
    print(f"It took {end_time-start_time:.2f} Time (s) to compute")


if __name__ == "__main__":
    main()