import csv
import json
import os

import pandas as pd
import plotly.utils
import numpy as np
import talib as tl
from flask import Flask, render_template, request
from datetime import datetime
import plotly.graph_objects as go

from patterns import patterns
import yfinance as yf

app = Flask(__name__)


@app.route('/')
def index():
    pattern = request.args.get('pattern', None)
    stocks = {}
    figs = {}
    dateparse = lambda x: datetime.strptime(x, '%Y-%m-%d')

    with open ('datasets/companies.csv') as f:
        for r in csv.reader(f):
            stocks[r[0]] = {'company': r[1]}
    if pattern:
        for filename in os.listdir('datasets/daily'):
            df = pd.read_csv('datasets/daily/{}'.format(filename), parse_dates=['Date'], infer_datetime_format=True, index_col='Date')
            if df.empty:
                continue
            symbol = filename.split('.')[0]
            try:
                pattern_function = getattr(tl, pattern)
                pattern_result = pattern_function(df['Open'], df['High'], df['Low'], df['Close'])
                if pattern_result.empty:
                    continue  # no pattern found, move on

                df['Pattern'] = pattern_result

                markers = df.loc[(df['Pattern'] != 0)]
                last_marker_date = markers.iloc[-1:].index[0]
                last_marker_value = markers.iloc[-1:]['Pattern'].values[0]

                window_start = last_marker_date - np.timedelta64(60, 'D')
                window_end = last_marker_date + np.timedelta64(30, 'D')
                zoom = df.loc[window_start:window_end]

                graph = go.Candlestick(x=df.index.tolist(),
                                       open=df['Open'].tolist(),
                                       high=df['High'].tolist(),
                                       low=df['Low'].tolist(),
                                       close=df['Close'].tolist(),
                                       name=symbol)
                data = [graph]
                layout = {'title': symbol}
                fig = dict(data=data, layout=layout)
                candle_fig = go.Figure(data=[graph])

                shapes = []
                for i, m in markers.iterrows():
                    shapes.append(dict(x0=i, x1=i, y0=0, y1=1, xref='x', yref='paper'))
#                    shapes = [dict(x0=last_marker_date, x1=last_marker_date, y0=0, y1=1, xref='x', yref='paper')]

                candle_fig.update_layout(shapes=shapes)
                # candle_fig.layout.xaxis.type = 'category'

                figs[symbol] = go.Figure(candle_fig).to_json()

                if last_marker_value > 0:
                    stocks[symbol][pattern] = 'bullish'
                elif last_marker_value < 0:
                    stocks[symbol][pattern] = 'bearish'
                else:
                    stocks[symbol][pattern] = None

                    print('{} triggered {}'.format(filename, pattern))
            except Exception as err:
                print(f"unexpected {err=}, {type(err)=}")
                pass

    return render_template('index.html', patterns=patterns, selected=pattern, stocks=stocks, graphs=figs)

@app.route('/snapshot')
def snapshot():
    with open('datasets/companies.csv') as f:
        companies = f.read().splitlines()
        for company in companies:
            symbol = company.split(',')[0]
            df = yf.download(symbol, start="2022-01-01", end="2022-11-01")
            df.to_csv('datasets/daily/{}.csv'.format(symbol))
    return {
        'code': 'success'
    }
