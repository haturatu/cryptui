# CryptUI

<img width="1220" height="546" alt="image" src="https://github.com/user-attachments/assets/3a353622-8610-4dca-ac68-8ef10b1426df" />

CryptUI is a command-line tool that displays real-time cryptocurrency price charts from Binance in your terminal. It supports real-time trade streams, candlestick charts, price-based notifications, and technical indicators.

## Features

-   **Real-Time Charts**: View live price action directly in your terminal.
-   **Candlestick Data**: Display historical candlestick charts for various intervals (e.g., 1m, 5m, 1h, 1d).
-   **Price Notifications**: Receive system-wide `wall` notifications when the price of a symbol crosses predefined thresholds.
-   **Technical Analysis**: Overlay technical indicators like Bollinger Bands on the chart.
-   **Customizable**: Adjust chart dimensions and indicator settings.

## Installation

1.  Clone this repository.
2.  Run the following command to build and install the tool:

    ```bash
    make install
    ```

    This will install the `cryptui` command and create the configuration directory at `/usr/local/etc/cryptui` with default settings.

    **Note:** Creating the `/usr/local/etc/cryptui` directory requires root privileges, so the `make install` command will use `sudo`. If you prefer not to install the tool system-wide, you can run the `cryptui.py` script directly from this root directory. When run directly, it will use the `config.ini` and `notification.md` files from the same directory.

## Usage

Run the script using the `cryptui` command.

```bash
$ cryptui -h
usage: cryptui [-h] [-s SYMBOL] [-i {1m,3m,5m,15m,30m,1h,2h,4h,6h,12h,1d,1w,1M}] [-H HEIGHT] [-w WIDTH]

Real-time crypto price chart from Binance with technical analysis and notifications.

options:
  -h, --help            show this help message and exit
  -s SYMBOL, --symbol SYMBOL
                        Symbol to display (e.g., BTCUSDT, ETHUSDT).
  -i {1m,3m,5m,15m,30m,1h,2h,4h,6h,12h,1d,1w,1M}, --interval {1m,3m,5m,15m,30m,1h,2h,4h,6h,12h,1d,1w,1M}
                        Show candlestick chart for a given interval.
                        If not provided, shows real-time trade stream.
  -H HEIGHT, --height HEIGHT
                        Chart height in lines (default: 15).
  -w WIDTH, --width WIDTH
                        Chart width in characters (default: 50).
```

### Basic Usage

To start a real-time price stream for BTCUSDT:

```bash
cryptui
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
cryptui --symbol ETHUSDT --interval 1h
```

**Start a real-time stream for DOGEUSDT with a custom chart height:**

```bash
cryptui -s DOGEUSDT -H 20
```

## Configuration

Configuration files are located in `/usr/local/etc/cryptui/`.

### Price Notifications (`notification.md`)

To receive price alerts, edit `/usr/local/etc/cryptui/notification.md`. The script will monitor the price of the selected symbol and send a `wall` message when it crosses the defined thresholds:

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

To configure technical indicators, edit `/usr/local/etc/cryptui/config.ini`. Currently, Bollinger Bands are supported.

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
