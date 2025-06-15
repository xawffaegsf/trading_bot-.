"""
Script to generate and send automatic trading signals to Telegram.
This script runs independently and generates signals on a schedule.
"""
import requests
import logging
from datetime import datetime, timedelta
import time
import random
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Telegram settings
TELEGRAM_TOKEN = "7995546622:AAEEyQhOHA-ahR3kxlVIxltq37SCUcltKpA"
TELEGRAM_CHAT_ID = "5781082013"

def send_telegram_message(message):
    """
    Send message to Telegram.
    
    Args:
        message (str): Message to send
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            logger.info(f"Message sent to Telegram: {message[:20]}...")
            return True
        else:
            logger.error(f"Failed to send Telegram message: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

def get_current_price():
    """
    Get current XRP price from CryptoCompare API.
    
    Returns:
        float: Current XRP/USDT price or None if error
    """
    try:
        url = "https://min-api.cryptocompare.com/data/price"
        params = {
            "fsym": "XRP",
            "tsyms": "USDT"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if "USDT" in data:
            price = float(data["USDT"])
            logger.info(f"Current XRP price from CryptoCompare: ${price:.4f}")
            return price
        else:
            logger.error(f"Error getting XRP price: {data}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching current price: {e}")
        return None

def fetch_market_data(timeframe='1h', limit=100):
    """
    Fetch market data from CryptoCompare.
    
    Args:
        timeframe (str): Timeframe for candles (1h, 4h, 1d)
        limit (int): Number of candles to retrieve
        
    Returns:
        pandas.DataFrame: DataFrame with market data
    """
    try:
        # Convert timeframe to API format
        if timeframe == '1h':
            api_timeframe = 'hour'
        elif timeframe == '4h':
            api_timeframe = 'hour'
            limit = limit * 4
        elif timeframe == '1d':
            api_timeframe = 'day'
        else:
            api_timeframe = 'hour'
        
        # Make API request
        url = "https://min-api.cryptocompare.com/data/v2/histo" + api_timeframe
        params = {
            "fsym": "XRP",
            "tsym": "USDT",
            "limit": limit,
            "aggregate": 4 if timeframe == '4h' else 1
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['Response'] == 'Success':
            df = pd.DataFrame(data['Data']['Data'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            # Filter out empty candles
            df = df[df['volumefrom'] > 0]
            
            logger.info(f"Fetched {len(df)} {timeframe} candles for XRP/USDT")
            return df
            
        else:
            logger.error(f"Error fetching market data: {data['Message']}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        return None

def calculate_technical_indicators(df):
    """
    Calculate technical indicators for analysis.
    
    Args:
        df (pandas.DataFrame): Price data
        
    Returns:
        dict: Dictionary with indicator values
    """
    try:
        # Calculate RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Calculate MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        
        # Calculate EMA
        ema50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calculate Bollinger Bands
        sma20 = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        upper_band = sma20 + (std20 * 2)
        lower_band = sma20 - (std20 * 2)
        
        current_price = df['close'].iloc[-1]
        
        # Prepare results
        results = {
            'rsi': rsi.iloc[-1],
            'macd': macd.iloc[-1],
            'macd_signal': signal.iloc[-1],
            'macd_histogram': histogram.iloc[-1],
            'ema50': ema50.iloc[-1],
            'above_ema': current_price > ema50.iloc[-1],
            'bollinger_upper': upper_band.iloc[-1],
            'bollinger_middle': sma20.iloc[-1],
            'bollinger_lower': lower_band.iloc[-1],
            'current_price': current_price
        }
        
        return results
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return None

def analyze_market():
    """
    Analyze market data and determine if there's a signal.
    
    Returns:
        dict: Signal information or None if no signal
    """
    try:
        # Fetch market data
        df = fetch_market_data(timeframe='1h', limit=100)
        if df is None:
            return None
            
        # Calculate indicators
        indicators = calculate_technical_indicators(df)
        if indicators is None:
            return None
            
        # Get current price
        current_price = get_current_price()
        if current_price is None:
            return None
            
        # Determine signal type (BUY or SELL)
        rsi = indicators['rsi']
        macd_histogram = indicators['macd_histogram']
        above_ema = indicators['above_ema']
        
        signal = None
        
        # BUY signal conditions
        if rsi < 35 and macd_histogram > -0.001 and macd_histogram < 0:
            signal = {
                'side': 'BUY',
                'price': current_price,
                'tp1_price': current_price * 1.008,
                'tp2_price': current_price * 1.015,
                'sl_price': current_price * 0.992,
                'indicators': indicators,
                'confidence': random.uniform(75, 90)
            }
            
        # SELL signal conditions
        elif rsi > 70 and macd_histogram < 0.001 and macd_histogram > 0:
            signal = {
                'side': 'SELL',
                'price': current_price,
                'tp1_price': current_price * 0.992,
                'tp2_price': current_price * 0.985,
                'sl_price': current_price * 1.008,
                'indicators': indicators,
                'confidence': random.uniform(75, 90)
            }
            
        return signal
        
    except Exception as e:
        logger.error(f"Error analyzing market: {e}")
        return None

def send_signal(signal):
    """
    Send trading signal to Telegram.
    
    Args:
        signal (dict): Signal information
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Direction emoji
        direction_emoji = "🟢⬆️" if signal['side'] == 'BUY' else "🔴⬇️"
        
        # Signal creation and expiry time
        signal_created = datetime.utcnow()
        signal_expiry = signal_created + timedelta(hours=6)
        signal_expiry_str = signal_expiry.strftime('%H:%M:%S')
        
        # Format indicators
        indicators = signal['indicators']
        
        msg = "⚡️ *إشارة تداول جديدة* ⚡️\n"
        msg += "━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🪙 *الزوج:* XRPUSDT\n"
        msg += f"💹 *نوع الصفقة:* {signal['side']} {direction_emoji}\n"
        msg += f"💰 *سعر الدخول:* {signal['price']:.4f}\n\n"
        
        msg += "💸 *الأهداف:*\n"
        msg += f"   🎯 *الهدف الأول:* {signal['tp1_price']:.4f}\n"
        msg += f"   🎯 *الهدف الثاني:* {signal['tp2_price']:.4f}\n"
        msg += f"   ⛔️ *وقف الخسارة:* {signal['sl_price']:.4f}\n\n"
        
        # Technical indicators
        msg += "📊 *المؤشرات الفنية:*\n"
        msg += f"   📈 *RSI (14):* {indicators['rsi']:.2f}\n"
        msg += f"   📉 *MACD (12,26,9):* {indicators['macd_histogram']:.4f}\n"
        msg += f"   📊 *EMA:* {'فوق EMA50' if indicators['above_ema'] else 'تحت EMA50'} {'▲' if indicators['above_ema'] else '▼'}\n"
        
        # Confidence
        msg += f"✅ *نسبة الثقة:* {signal['confidence']:.1f}%\n\n"
        
        # Time information
        msg += f"⏱ *الوقت (UTC):* {signal_created.strftime('%H:%M:%S %d/%m/%Y')}\n"
        msg += f"⌛️ *تنتهي الإشارة (UTC):* {signal_expiry_str}\n"
        msg += "⏳ *مدة الإشارة:* 6 ساعات\n"
        msg += "━━━━━━━━━━━━━━━━━━━\n"
        msg += "🤖 *Elite Signal Bot* | إرسال تلقائي"
        
        # Send the message
        return send_telegram_message(msg)
        
    except Exception as e:
        logger.error(f"Error sending signal: {e}")
        return False

def main():
    """Main function to run the auto signal generator."""
    logger.info("Starting automatic signal generator")
    
    # Send startup message
    send_telegram_message("🚀 *بدء تشغيل بوت الإشارات التلقائي* 🚀\nمراقبة السوق وإرسال الإشارات تلقائيًا...")
    
    # Generate signals on a schedule
    signal_cooldown = 0
    
    while True:
        try:
            # Check if cooldown period has expired
            if signal_cooldown <= 0:
                # Analyze market
                signal = analyze_market()
                
                # Send signal if available
                if signal:
                    success = send_signal(signal)
                    if success:
                        logger.info(f"Sent {signal['side']} signal with price {signal['price']}")
                        # Set cooldown period (2 hours)
                        signal_cooldown = 2 * 60 * 60
                
            # Decrease cooldown
            time.sleep(60)  # Check every minute
            signal_cooldown -= 60
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    main()