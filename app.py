import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
from sqlalchemy import func

from models import session, Nem12Record300, Nem12Record200, EnergyUsage

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

rows = session.query(EnergyUsage.timestamp, func.sum(EnergyUsage.energy_usage)).\
    group_by(EnergyUsage.timestamp).\
    order_by(EnergyUsage.timestamp).\
    all()

df_30min = pd.DataFrame(rows, columns=["timestamp", "energy_usage"])
df_daily = df_30min.groupby(pd.Grouper(key='timestamp', freq='D'))['energy_usage'] \
        .sum() \
        .reset_index() \
        .sort_values('timestamp')
df_rolling_weekly = df_daily.rolling(window=7, center=True, on='timestamp').mean()

app.layout = html.Div([
    dcc.Graph(
        id='example-graph',
        figure={
            'data': [
                go.Bar(x=df_daily['timestamp'], y=df_daily['energy_usage']),
                go.Scatter(x=df_rolling_weekly['timestamp'], y=df_rolling_weekly['energy_usage'])
            ],
            'layout': go.Layout(yaxis={"title": "[kWh]"}, xaxis={"rangeslider": {"visible": True}})
        }
    )
])

if __name__ == '__main__':
    app.run_server(debug=True, host="192.168.20.5", ssl_context='adhoc')
