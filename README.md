"""
Web application for the cryptocurrency trading signal bot dashboard.
"""
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from models import db, Signal, Strategy
from sqlalchemy import desc
import json
from decimal import Decimal

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_secret_key")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

@app.route('/')
def index():
    """Home page - Dashboard."""
    # Get latest signals
    signals = Signal.query.order_by(desc(Signal.created_at)).limit(10).all()
    signals_dict = [signal.to_dict() for signal in signals]
    
    # Get strategies
    strategies = Strategy.query.order_by(Strategy.id).all()
    strategies_dict = [strategy.to_dict() for strategy in strategies]
    
    # Get performance data for display
    total = Signal.query.count()
    tp1_hit = Signal.query.filter_by(status='TP1_HIT').count()
    tp2_hit = Signal.query.filter_by(status='TP2_HIT').count()
    sl_hit = Signal.query.filter_by(status='SL_HIT').count()
    active = Signal.query.filter_by(status='ACTIVE').count()
    
    # Calculate win rate
    win_rate = ((tp1_hit + tp2_hit) / total * 100) if total > 0 else 0
    
    return render_template('index.html', 
                           signals=signals_dict, 
                           strategies=strategies_dict, 
                           win_rate=round(win_rate, 2),
                           total_signals=total,
                           tp1_hit=tp1_hit,
                           tp2_hit=tp2_hit,
                           sl_hit=sl_hit,
                           active=active)

@app.route('/signals')
def signals():
    """Signals page."""
    signals = Signal.query.order_by(desc(Signal.created_at)).all()
    return render_template('signals.html', signals=[signal.to_dict() for signal in signals])

@app.route('/performance')
def performance():
    """Performance analysis page."""
    return render_template('performance.html')

@app.route('/advanced')
def advanced():
    """Advanced strategy analysis page."""
    return render_template('advanced_strategy.html')

@app.route('/strategies')
def strategies():
    """Strategies page."""
    strategies = Strategy.query.order_by(Strategy.id).all()
    return render_template('strategies.html', strategies=[strategy.to_dict() for strategy in strategies])

@app.route('/strategies/add', methods=['GET', 'POST'])
def add_strategy():
    """Add new strategy."""
    if request.method == 'POST':
        # Create a new strategy
        strategy = Strategy()
        # Basic info
        strategy.name = request.form['name']
        strategy.description = request.form['description']
        strategy.symbol = request.form['symbol']
        
        # Basic indicators
        strategy.rsi_period = request.form.get('rsi_period', 14)
        strategy.rsi_lower = request.form['rsi_lower']
        strategy.rsi_upper = request.form['rsi_upper']
        strategy.macd_enabled = bool(request.form.get('macd_enabled'))
        strategy.macd_fast = request.form.get('macd_fast', 12)
        strategy.macd_slow = request.form.get('macd_slow', 26)
        strategy.macd_signal = request.form.get('macd_signal', 9)
        strategy.ema_enabled = bool(request.form.get('ema_enabled'))
        strategy.ema_period = request.form['ema_period']
        
        # Advanced indicators
        strategy.bollinger_enabled = bool(request.form.get('bollinger_enabled'))
        strategy.bollinger_period = request.form.get('bollinger_period', 20)
        strategy.bollinger_std = request.form.get('bollinger_std', 2.0)
        strategy.stochastic_enabled = bool(request.form.get('stochastic_enabled'))
        strategy.stochastic_k = request.form.get('stochastic_k', 14)
        strategy.stochastic_d = request.form.get('stochastic_d', 3)
        strategy.stochastic_lower = request.form.get('stochastic_lower', 20)
        strategy.stochastic_upper = request.form.get('stochastic_upper', 80)
        
        # Risk management
        strategy.tp1_multiplier = request.form['tp1_multiplier']
        strategy.tp2_multiplier = request.form['tp2_multiplier']
        strategy.sl_multiplier = request.form['sl_multiplier']
        strategy.risk_reward_ratio = request.form.get('risk_reward_ratio', 2.0)
        strategy.position_size_percent = request.form.get('position_size_percent', 1.0)
        
        # Status
        strategy.is_active = bool(request.form.get('is_active'))
        db.session.add(strategy)
        db.session.commit()
        flash('تم إضافة الاستراتيجية بنجاح!', 'success')
        return redirect(url_for('strategies'))
    return render_template('add_strategy.html')

@app.route('/strategies/edit/<int:id>', methods=['GET', 'POST'])
def edit_strategy(id):
    """Edit strategy."""
    strategy = Strategy.query.get_or_404(id)
    if request.method == 'POST':
        strategy.name = request.form['name']
        strategy.description = request.form['description']
        strategy.symbol = request.form['symbol']
        strategy.rsi_lower = request.form['rsi_lower']
        strategy.rsi_upper = request.form['rsi_upper']
        strategy.macd_enabled = bool(request.form.get('macd_enabled'))
        strategy.ema_enabled = bool(request.form.get('ema_enabled'))
        strategy.ema_period = request.form['ema_period']
        strategy.tp1_multiplier = request.form['tp1_multiplier']
        strategy.tp2_multiplier = request.form['tp2_multiplier']
        strategy.sl_multiplier = request.form['sl_multiplier']
        strategy.is_active = bool(request.form.get('is_active'))
        db.session.commit()
        flash('تم تحديث الاستراتيجية بنجاح!', 'success')
        return redirect(url_for('strategies'))
    return render_template('edit_strategy.html', strategy=strategy.to_dict())

@app.route('/api/signals')
def api_signals():
    """API endpoint for signals."""
    signals = Signal.query.order_by(desc(Signal.created_at)).limit(50).all()
    return jsonify([signal.to_dict() for signal in signals])

@app.route('/api/strategies')
def api_strategies():
    """API endpoint for strategies."""
    strategies = Strategy.query.all()
    return jsonify([strategy.to_dict() for strategy in strategies])

@app.route('/api/signals/performance')
def api_signals_performance():
    """API endpoint for signal performance analytics."""
    # Count signals by status
    total = Signal.query.count()
    tp1_hit = Signal.query.filter_by(status='TP1_HIT').count()
    tp2_hit = Signal.query.filter_by(status='TP2_HIT').count()
    sl_hit = Signal.query.filter_by(status='SL_HIT').count()
    active = Signal.query.filter_by(status='ACTIVE').count()
    
    # Calculate win rate
    win_rate = ((tp1_hit + tp2_hit) / total * 100) if total > 0 else 0
    
    # Calculate average profit/loss percentage
    avg_profit_pct = 0
    total_closed = tp1_hit + tp2_hit + sl_hit
    
    if total_closed > 0:
        closed_signals = Signal.query.filter(Signal.status.in_(['TP1_HIT', 'TP2_HIT', 'SL_HIT'])).all()
        total_pnl_pct = sum(float(s.profit_loss_percent) for s in closed_signals if s.profit_loss_percent is not None)
        avg_profit_pct = total_pnl_pct / total_closed if total_closed > 0 else 0
    
    # Calculate average trade duration
    avg_duration = 0
    signals_with_duration = Signal.query.filter(Signal.duration_minutes.isnot(None)).count()
    
    if signals_with_duration > 0:
        total_duration = db.session.query(db.func.sum(Signal.duration_minutes)).scalar() or 0
        avg_duration = total_duration / signals_with_duration if signals_with_duration > 0 else 0
    
    return jsonify({
        'total': total,
        'tp1_hit': tp1_hit,
        'tp2_hit': tp2_hit,
        'sl_hit': sl_hit,
        'active': active,
        'win_rate': round(win_rate, 2),
        'avg_profit_pct': round(avg_profit_pct, 2),
        'avg_duration_minutes': round(avg_duration)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
