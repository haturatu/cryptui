# CryptUI

CryptUI is a command-line tool that displays real-time cryptocurrency price charts from Binance in your terminal. It supports real-time trade streams, candlestick charts, price-based notifications, and technical indicators.

## Features

-   **Real-Time Charts**: View live price action directly in your terminal.
-   **Candlestick Data**: Display historical candlestick charts for various intervals (e.g., 1m, 5m, 1h, 1d).
-   **Price Notifications**: Receive system-wide `wall` notifications when the price of a symbol crosses predefined thresholds.
-   **Technical Analysis**: Overlay technical indicators like Bollinger Bands on the chart.
-   **Customizable**: Adjust chart dimensions and indicator settings.

## Installation

1.  Clone the repository or download the source code.
2.  Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the script using `python cryptui.py`.

### Basic Usage

To start a real-time price stream for BTCUSDT:

```bash
python cryptui.py
```

### Command-Line Arguments

-   `-s`, `--symbol`: The symbol to display (e.g., `ETHUSDT`, `XRPUSDT`). Defaults to `BTCUSDT`.
-   `-i`, `--interval`: The candlestick interval. If omitted, shows a real-time stream.
    -   *Available intervals*: `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `12h`, `1d`, `1w`, `1M`.
-   `-H`, `--height`: The height of the chart in lines.
-   `-w`, `--width`: The width of the chart in characters.

### Examples

**Show a 1-hour candlestick chart for ETHUSDT:**

```bash
python cryptui.py --symbol ETHUSDT --interval 1h
```

**Start a real-time stream for DOGEUSDT with a custom chart height:**

```bash
python cryptui.py -s DOGEUSDT -H 20
```

## Configuration

### Price Notifications (`notification.md`)

To receive price alerts, create a file named `notification.md` in the same directory. The script will monitor the price of the selected symbol and send a `wall` message when it crosses the defined thresholds:

-   `less`: Notifies when the price becomes **less than or equal to** this value.
-   `more`: Notifies when the price becomes **greater than or equal to** this value.

The notification will only trigger once when the threshold is crossed. It resets after the price returns between the two thresholds.

**Example `notification.md`:**

```markdown
- BTCUSDT
  - less: 102000
  - more: 104000
- ETHUSDT
  - less: 3000
  - more: 3500
```

### Technical Indicators (`config.ini`)

To configure technical indicators, create a `config.ini` file. Currently, Bollinger Bands are supported.

**Example `config.ini`:**

```ini
[technical_indicators]
# To display Bollinger Bands, set to 'yes'. Any other value will disable it.
bollinger_bands = yes
# The period for the Simple Moving Average and Standard Deviation.
bollinger_period = 20
# The number of standard deviations for the upper and lower bands.
bollinger_std_dev = 2
```

## Dependencies

-   `httpx`
-   `websockets`
-   `asciichartpy`