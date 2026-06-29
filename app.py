# Finance Dashboard
# A real-time interactive finance dashboard built with Streamlit that tracks live stock data across NASDAQ and LSE using the Yahoo Finance API.
# Using technical indictors such as RSI built from scratch to provide insights into stock performance.


# --- Imports ---

# streamlit: turns this Python script into an interactive web application
# yfinance: wrapper around Yahoo Finance API for free real-time stock data
# pandas: industry standard library for manipulating tabular data
# plotly.graph_objects: low-level Plotly API giving full control over charts

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go


# --- Streamlit App Configuration ---

st.set_page_config(page_title="Finance Dashboard", layout="wide")
st.title("Finance Dashboard")
st.caption("Tracking Stock Data")


# --- Sidebar ---

# Sidebar allows users to select the date range for stock data and choose which stocks to display on the dashboard,
# keeping it seperate from the main content area and providing a clean user interface.

with st.sidebar:
    st.title("Settings")
    st.subheader("Date Range")
    period = st.selectbox(
        "Select period",
        options=["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"],
        index=3,
        format_func=lambda x: {
            "1mo": "1 Month",
            "3mo": "3 Months",
            "6mo": "6 Months",
            "1y": "1 Year",
            "2y": "2 Years",
            "5y": "5 Years",
            "10y": "10 Years",
            "max": "Max"
        }[x]
    )

    st.subheader("Stocks")
    show_nvda = st.checkbox("Show Nvidia (NVDA)", value=True)
    show_gaw = st.checkbox("Show Games Workshop (GAW.L)", value=True)
    show_capita = st.checkbox("Show Capita (CPI.L)", value=True)

    st.divider()
    st.caption("Data sourced from Yahoo Finance via yfinance. Refreshes every hour.")


# --- Data Loading ---

# @st.cache_data caches the result of this function so it doesn't re-download data on every user interaction.
# ttl=3600 sets the cache to expire after 1 hour, ensuring that the dashboard displays relatively fresh data without overwhelming the Yahoo Finance API with requests.

@st.cache_data(ttl=3600)
def load_data(ticker, period="1y"):
    # Download historical stock data from Yahoo Finance for the given ticker and period.
    df = yf.download(ticker, period=period, auto_adjust=True)
    # Drop any rows with missing values to ensure clean data for analysis and visualization.
    df.dropna(inplace=True)
    # Convert the index to datetime and remove timezone information as was gettiing erros with plotly.
    df.index = pd.to_datetime(df.index).tz_localize(None)
    # If the DataFrame has multi-level columns (MultiIndex), flatten them to a single level for easier handling.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# Load data for each stock
nvda = load_data("NVDA", period=period)
gaw = load_data("GAW.L", period=period)
capita = load_data("CPI.L", period=period)


# --- Currency normalization ---

# The stock data for Games Workshop is in pence so we convert it into pounds for better readability.
# For stocks of lower price like Capita, we keep it in pence to keep the numbers more readable and avoid decimals in the display.

for col in ["Open", "High", "Low", "Close"]:
    gaw[col] = gaw[col] / 100


# --- Metrics Display ---

# Display key metrics for each stock, including current price, daily change percentage, 52-week high, and 52-week low.
# Gives users a quick overview of the stock's performance and recent trends.

def show_metrics(df, ticker, currency):
    # iloc[-1] gets the last row of the DataFrame, which corresponds to the most recent trading day.
    # iloc[-2] gets the second-to-last row, which corresponds to the previous trading day.
    current = df["Close"].iloc[-1]
    prev = df["Close"].iloc[-2]
    # Calculate the percentage change from the previous close to the current close.
    change = ((current - prev) / prev) * 100
    # Calculate the 52-week high and low by finding the maximum and minimum closing prices in the DataFrame.
    high_52w = df["Close"].max()
    low_52w = df["Close"].min()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"{currency}{current:.2f}")
    col2.metric("Daily Change", f"{change:.2f}%", f"{change:.2f}%")
    col3.metric("52w High", f"{currency}{high_52w:.2f}")
    col4.metric("52w Low", f"{currency}{low_52w:.2f}")


# --- Candlestick Chart ---

# Display a candlestick chart for each stock, showing the open, high, low, and close prices over time. One candle respresents one trading day.
# The chart also includes a 20-day moving average line to help visualize trends and potential support/resistance levels.

def plot_candlestick(df, ticker, color):

    # Work on a copy of the DataFrame to avoid modifying the original data.
    df = df.copy()
    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["prev_close"] = df["Close"].shift(1)

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="OHLC",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350"
    ))

    # Add a 20-day moving average line to the chart to help visualize trends.
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["MA20"],
        mode="lines",
        name="20d MA",
        line=dict(color="orange", width=1.5, dash="dot")
    ))

    # Dark theme for the chart with gridlines for better readabiltiy.
    fig.update_layout(
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#1e1e1e",
        font=dict(color="#e0e0e0"),
        xaxis=dict(gridcolor="#2e2e2e", showgrid=True),
        yaxis=dict(gridcolor="#2e2e2e", showgrid=True),
        xaxis_title="Date",
        yaxis_title=f"Price",
        hovermode="x unified",
        height=500,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )
    return fig

# --- Volume Chart ---
# Displays the number of shares traded each day as a bar chart
# Volume confirms whether a price move has real conviction behind it
# A big price move on high volume is significant
# The same move on low volume may be unreliable
def plot_volume(df, currency):
    df = df.copy()
    colors = ["#26a69a" if c >= p else "#ef5350"
              for c, p in zip(df["Close"], df["Close"].shift(1))]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df.index,
        y=df["Volume"],
        marker_color=colors,
        name="Volume",
        opacity=0.8
    ))
    fig.update_layout(
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#1e1e1e",
        font=dict(color="#e0e0e0"),
        xaxis=dict(gridcolor="#2e2e2e", showgrid=True),
        yaxis=dict(gridcolor="#2e2e2e", showgrid=True),
        hovermode="x unified",
        height=200,
        margin=dict(l=20, r=20, t=10, b=20),
        showlegend=False,
        yaxis_title="Volume"
    )
    return fig

# --- RSI Calculation ---
# RSI (Relative Strength Index) measures momentum on a 0-100 scale
# Built from scratch using raw maths rather than importing a library
def calculate_rsi(df, period=14):
    df = df.copy()
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

def plot_rsi(df):
    df = calculate_rsi(df)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["RSI"],
        mode="lines",
        name="RSI",
        line=dict(color="#7b61ff", width=2)
    ))

    # Overbought line
    fig.add_hline(y=70, line_dash="dash",
                  line_color="#ef5350", opacity=0.7,
                  annotation_text="Overbought (70)",
                  annotation_position="bottom right",
                  annotation_font_color="#ef5350")

    # Oversold line
    fig.add_hline(y=30, line_dash="dash",
                  line_color="#26a69a", opacity=0.7,
                  annotation_text="Oversold (30)",
                  annotation_position="top right",
                  annotation_font_color="#26a69a")

    fig.update_layout(
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#1e1e1e",
        font=dict(color="#e0e0e0"),
        xaxis=dict(gridcolor="#2e2e2e", showgrid=True),
        yaxis=dict(gridcolor="#2e2e2e", showgrid=True,
                   range=[0, 100]),
        hovermode="x unified",
        height=250,
        margin=dict(l=20, r=20, t=10, b=20),
        showlegend=False,
        yaxis_title="RSI"
    )
    return fig

# --- Nvidia Section ---
if show_nvda:
    st.subheader("Nvidia (NVDA)")
    show_metrics(nvda, "NVDA", "$")
    st.plotly_chart(plot_candlestick(nvda, "NVDA", "#76b900"), use_container_width=True)
    st.plotly_chart(plot_volume(nvda, "$"), use_container_width=True)
    st.plotly_chart(plot_rsi(nvda), use_container_width=True)
    st.divider()

# --- Games Workshop Section ---
if show_gaw:
    st.subheader("Games Workshop (GAW.L)")
    show_metrics(gaw, "GAW.L", "£")
    st.plotly_chart(plot_candlestick(gaw, "GAW.L", "#e3000f"), use_container_width=True)
    st.plotly_chart(plot_volume(gaw, "£"), use_container_width=True)
    st.plotly_chart(plot_rsi(gaw), use_container_width=True)

# --- Capita Section ---
if show_capita:
    st.subheader("Capita (CPI.L)")
    show_metrics(capita, "CPI.L", "p")
    st.plotly_chart(plot_candlestick(capita, "CPI.L", "#ff9800"), use_container_width=True)
    st.plotly_chart(plot_volume(capita, "p"), use_container_width=True)
    st.plotly_chart(plot_rsi(capita), use_container_width=True)