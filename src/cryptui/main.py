import asyncio
import json
import os
import sys
import httpx
import websockets
import asciichartpy
import argparse
import re
from collections import deque
from datetime import datetime
import configparser
import statistics
import math

# Optional: Technical Indicators
# Bollinger Bands Calculation
def calculate_bollinger_bands(prices, period=20, std_dev_multiplier=2):
    """Calculates Bollinger Bands for a given price series."""
    # Use float('nan') for points where the bands cannot be calculated.
    nan = float('nan')
    if len(prices) < period:
        return ([nan] * len(prices), [nan] * len(prices), [nan] * len(prices))

    middle_bands = [nan] * (period - 1)
    upper_bands = [nan] * (period - 1)
    lower_bands = [nan] * (period - 1)

    for i in range(period - 1, len(prices)):
        window = prices[i - period + 1 : i + 1]
        # Ensure window has enough data points for stdev
        if len(window) < 2:
             middle_bands.append(nan)
             upper_bands.append(nan)
             lower_bands.append(nan)
             continue
        sma = statistics.mean(window)
        std_dev = statistics.stdev(window)
        
        middle_bands.append(sma)
        upper_bands.append(sma + std_dev * std_dev_multiplier)
        lower_bands.append(sma - std_dev * std_dev_multiplier)

    return lower_bands, middle_bands, upper_bands

# configurable parameters
CHART_HEIGHT = 15
#CHART_WIDTH = 80
CHART_WIDTH = 50
TIME_AXIS_FORMAT = "%m-%d %H:%M"

# Deque for non-interval mode
stream_prices = deque(maxlen=CHART_WIDTH)
# Deque for interval mode (stores only closed candles)
historical_prices = deque(maxlen=CHART_WIDTH - 1)
# Variable for the live, unclosed candle in interval mode
live_price_tuple = None

BINANCE_INTERVALS = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w", "1M"]

# Notification Handling
def parse_notification_rules(content: str, symbol: str) -> dict | None:
    """Parses notification rules from the content of notification.md."""
    symbol_block_match = re.search(rf'- {re.escape(symbol)}(.*?)(?=\n- \w+USDT|\Z)', content, re.DOTALL | re.MULTILINE)
    if not symbol_block_match:
        return None
    block = symbol_block_match.group(1)
    less_match = re.search(r'less\s*\n\s*-?\s*([0-9.]+)', block, re.MULTILINE)
    more_match = re.search(r'more\s*\n\s*-?\s*([0-9.]+)', block, re.MULTILINE)
    if less_match and more_match:
        try:
            return {'less': float(less_match.group(1)), 'more': float(more_match.group(1))}
        except ValueError:
            return None
    return None

async def send_notifications_background(message: str):
    """Sends 3 wall notifications in the background with a 10s delay."""
    print(f"--- Starting background notification task for: {message} ---")
    for i in range(3):
        proc = await asyncio.create_subprocess_shell(f"wall {message}")
        await proc.wait()
        if i < 2:
            await asyncio.sleep(10)
    print(f"--- Finished background notification task for: {message} ---")

async def check_notifications(price: float, rules: dict, state: dict):
    """Checks the price against the rules and queues background notifications."""
    less_threshold, more_threshold, symbol = rules.get('less'), rules.get('more'), rules.get('symbol')
    notification_sent, message = False, ""
    if price <= less_threshold and not state['less_triggered']:
        message = f"'{symbol} price alert: Dropped below {less_threshold}! Current: {price}'"
        state.update({'less_triggered': True, 'more_triggered': False})
        notification_sent = True
    elif price >= more_threshold and not state['more_triggered']:
        message = f"'{symbol} price alert: Rose above {more_threshold}! Current: {price}'"
        state.update({'more_triggered': True, 'less_triggered': False})
        notification_sent = True
    elif less_threshold < price < more_threshold:
        state.update({'less_triggered': False, 'more_triggered': False})
    if notification_sent:
        print(f"--- QUEUING BACKGROUND NOTIFICATION: {message} ---")
        asyncio.create_task(send_notifications_background(message))

# ohclv Fetching
async def fetch_historical_klines(client: httpx.AsyncClient, symbol: str, interval: str, limit: int):
    print(f"Fetching historical {interval} data for {symbol} from Binance...")
    data = []
    try:
        url = "https://fapi.binance.com/fapi/v1/klines"
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        response = await client.get(url, params=params)
        response.raise_for_status()
        klines = response.json()
        data = [(int(k[0]), float(k[4])) for k in klines]
    except Exception as e:
        print(f"Could not fetch historical data from Binance: {e}")
    return data

# ws Appenders
async def kline_appender(symbol: str, interval: str):
    """Connects to kline stream and appends closed candles to historical_prices."""
    url = f"wss://fstream.binance.com/ws/{symbol.lower()}@kline_{interval}"
    async for ws in websockets.connect(url):
        try:
            while True:
                data = json.loads(await ws.recv())
                if data.get('k', {}).get('x'):
                    kline = data['k']
                    historical_prices.append((int(kline['t']), float(kline['c'])))
        except websockets.exceptions.ConnectionClosed:
            print("Kline appender connection closed. Reconnecting...")
            await asyncio.sleep(1)

async def live_price_updater(symbol: str):
    """Connects to aggTrade stream and updates the live_price_tuple."""
    global live_price_tuple
    url = f'wss://fstream.binance.com/ws/{symbol.lower()}@aggTrade'
    async for ws in websockets.connect(url):
        try:
            while True:
                data = json.loads(await ws.recv())
                live_price_tuple = (int(data['T']), float(data['p']))
        except websockets.exceptions.ConnectionClosed:
            print("Live price updater connection closed. Reconnecting...")
            await asyncio.sleep(1)

async def fetch_stream(symbol: str):
    """For non-interval mode. Connects to aggTrade and appends to stream_prices."""
    url = f'wss://fstream.binance.com/ws/{symbol.lower()}@aggTrade'
    async for ws in websockets.connect(url):
        try:
            while True:
                data = json.loads(await ws.recv())
                stream_prices.append((int(data['T']), float(data['p'])))
        except websockets.exceptions.ConnectionClosed:
            print("Stream connection closed. Reconnecting...")
            await asyncio.sleep(1)

# UI Drawing Loop
def generate_time_axis(timestamps: list[int], width: int) -> str:
    if not timestamps:
        return ' ' * width

    # Convert timestamp to local time
    first_dt = datetime.fromtimestamp(timestamps[0] / 1000)

    axis = [' '] * width
    first_str = first_dt.strftime(TIME_AXIS_FORMAT)

    for i, c in enumerate(first_str):
        if i < width:
            axis[i] = c

    # center timestamp
    mid_ts = timestamps[len(timestamps)//2]
    mid_dt = datetime.fromtimestamp(mid_ts / 1000)
    mid_str = mid_dt.strftime("%H:%M")
    mid_pos = width // 2 - len(mid_str) // 2
    for i, c in enumerate(mid_str):
        pos = mid_pos + i
        if 0 <= pos < width and axis[pos] == ' ':
            axis[pos] = c

    return ''.join(axis)

# Drawing Loop
# Note: This function clears the terminal and redraws the chart every 0.1 seconds.
# sys.stdout.write("\033[2J\033[H") is used to clear the terminal.
async def drawing_loop(symbol: str, interval: str | None, notification_rules: dict | None, notification_state: dict | None, tech_indicators_config: dict | None):
    while True:
        sys.stdout.write("\033[2J\033[H")
        title = f"{symbol} Candlestick Chart ({interval})" if interval else f"{symbol} Real-Time Stream"
        
        combined_data = []
        if interval:
            combined_data = list(historical_prices)
            if live_price_tuple:
                combined_data.append(live_price_tuple)
        else:
            combined_data = list(stream_prices)

        plot_prices = [p for ts, p in combined_data]
        timestamps = [ts for ts, p in combined_data]
        
        price_str = f"{plot_prices[-1]:.2f}" if plot_prices else "N/A"

        header_left = f"Binance: {price_str}"
        header_right = ""
        if timestamps:
            last_dt = datetime.fromtimestamp(timestamps[-1] / 1000)
            header_right = f"Last: {last_dt.strftime('%H:%M:%S')}"
        
        header = f"{header_left}{header_right:>{CHART_WIDTH - len(header_left)}}"
        
        out_lines = []
        out_lines.append(title.ljust(CHART_WIDTH))
        out_lines.append(header.ljust(CHART_WIDTH))

        if not plot_prices:
            out_lines.append("\n" * (CHART_HEIGHT + 1))
            out_lines.append("Waiting for data...".ljust(CHART_WIDTH))
        else:
            if notification_rules and notification_state:
                await check_notifications(plot_prices[-1], notification_rules, notification_state)

            # plotting
            plot_series = [plot_prices]
            new_chart_width = CHART_WIDTH - 10
            plot_config = {
                'height': CHART_HEIGHT,
                'width': new_chart_width,
            }

            # Optional Technical Indicators
            # Bollinger Bands
            # collor scheme: lower (blue), middle (yellow), upper (blue), price (default)
            if tech_indicators_config and tech_indicators_config.get('bollinger_bands') == 'yes':
                period = tech_indicators_config.get('bollinger_period', 20)
                std_dev = tech_indicators_config.get('bollinger_std_dev', 2)
                lower, middle, upper = calculate_bollinger_bands(plot_prices, period, std_dev)
                
                plot_series = [lower, middle, upper, plot_prices]
                plot_config['colors'] = [
                    asciichartpy.blue,
                    asciichartpy.yellow,
                    asciichartpy.blue,
                    asciichartpy.default,
                ]

            # Determine min/max from all series to be plotted
            all_plot_values = [item for series in plot_series for item in series if not math.isnan(item)]
            if not all_plot_values:
                all_plot_values = [0] # Avoid crashing if all are nan

            min_price, max_price, last_price = min(all_plot_values), max(all_plot_values), plot_prices[-1]
            
            # Determine the maximum width for y-axis labels to ensure consistent chart alignment.
            y_axis_label_width = max(len(f"{p:.2f}") for p in [min_price, max_price]) if all_plot_values else 8
            plot_config['format'] = f'{{:>{y_axis_label_width}.2f}}'

            right_axis_labels, price_range = [], max_price - min_price
            
            for i in range(CHART_HEIGHT):
                percentage = 0.0
                if price_range > 0 and last_price > 0:
                    price_at_row = max_price - (i * price_range / (CHART_HEIGHT - 1 if CHART_HEIGHT > 1 else 1))
                    percentage = ((price_at_row / last_price) - 1) * 100
                right_axis_labels.append(f"{percentage:+8.2f}%")

            chart_str = asciichartpy.plot(plot_series, plot_config)
            chart_lines = chart_str.split('\n')
            combined_chart = [line + " " + right_axis_labels[i] if i < len(right_axis_labels) else line for i, line in enumerate(chart_lines)]
            
            for i, line in enumerate(combined_chart):
                out_lines.append(line.ljust(CHART_WIDTH))

            # --- Time Axis Alignment Fix ---
            gutter_width = 0
            plot_area_width = new_chart_width
            if chart_lines:
                separator_pos = chart_lines[0].find('┤')
                if separator_pos != -1:
                    gutter_width = separator_pos + 1
                    plot_area_width = new_chart_width - gutter_width

            time_axis_core = generate_time_axis(timestamps, plot_area_width)
            final_time_axis = (' ' * gutter_width) + time_axis_core
            final_time_axis = final_time_axis.ljust(CHART_WIDTH)
            out_lines.append(final_time_axis.ljust(CHART_WIDTH))

        sys.stdout.write("\n".join(out_lines) + "\n")
        sys.stdout.flush()

        await asyncio.sleep(0.1)

# main
def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nCharts closed.")
    except Exception as e:
        print(f"An error occurred: {e}")

async def async_main():
    global CHART_HEIGHT, CHART_WIDTH, stream_prices, historical_prices

    parser = argparse.ArgumentParser(description='Real-time crypto price chart from Binance with technical analysis and notifications.', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-s', '--symbol', default='BTCUSDT', help='Symbol to display (e.g., BTCUSDT, ETHUSDT).')
    parser.add_argument('-i', '--interval', default=None, choices=BINANCE_INTERVALS, help='Show candlestick chart for a given interval.\nIf not provided, shows real-time trade stream.')
    parser.add_argument('-H', '--height', type=int, default=CHART_HEIGHT, help=f'Chart height in lines (default: {CHART_HEIGHT}).')
    parser.add_argument('-w', '--width', type=int, default=CHART_WIDTH, help=f'Chart width in characters (default: {CHART_WIDTH}).')
    args = parser.parse_args()

    # Override globals with args
    CHART_HEIGHT = args.height
    CHART_WIDTH = args.width
    stream_prices = deque(maxlen=CHART_WIDTH)
    historical_prices = deque(maxlen=CHART_WIDTH - 1)

    # --- Config File Loading ---
    CONFIG_DIR = os.path.expanduser("~/.config/cryptui")
    config = configparser.ConfigParser()
    tech_indicators_config = {}
    try:
        config_path = os.path.join(CONFIG_DIR, 'config.ini')
        config.read(config_path)
        if 'technical_indicators' in config:
            ti_section = config['technical_indicators']
            tech_indicators_config['bollinger_bands'] = ti_section.get('bollinger_bands', 'no')
            tech_indicators_config['bollinger_period'] = ti_section.getint('bollinger_period', 20)
            tech_indicators_config['bollinger_std_dev'] = ti_section.getfloat('bollinger_std_dev', 2)
            if tech_indicators_config.get('bollinger_bands') == 'yes':
                print("Bollinger Bands enabled.")
    except Exception as e:
        print(f"Could not read or parse {config_path}: {e}")


    notification_rules, notification_state = None, None
    try:
        notification_path = os.path.join(CONFIG_DIR, 'notification.md')
        with open(notification_path, 'r') as f:
            notification_rules = parse_notification_rules(f.read(), args.symbol)
        if notification_rules:
            print(f"Notification rules loaded for {args.symbol}: Less < {notification_rules['less']}, More > {notification_rules['more']}")
            notification_state = {'less_triggered': False, 'more_triggered': False}
            notification_rules['symbol'] = args.symbol
    except FileNotFoundError:
        print(f"{notification_path} not found, skipping notification feature.")
    except Exception as e:
        print(f"Error loading notification rules: {e}")

    tasks = []
    if args.interval:
        async with httpx.AsyncClient() as client:
            hist_data = await fetch_historical_klines(client, args.symbol, args.interval, CHART_WIDTH - 1)
            if hist_data:
                historical_prices.extend(hist_data)
        tasks.append(kline_appender(args.symbol, args.interval))
        tasks.append(live_price_updater(args.symbol))
    else:
        tasks.append(fetch_stream(args.symbol))

    tasks.append(drawing_loop(args.symbol, args.interval, notification_rules, notification_state, tech_indicators_config))
    
    mode = f"{args.interval} candlestick" if args.interval else "real-time stream"
    print(f"Starting {mode} display for {args.symbol}... Press Ctrl+C to exit.")
    await asyncio.sleep(2)
    print("\033[H\033[J", end="")
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    main()
