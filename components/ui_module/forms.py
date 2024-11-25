# components/ui_module/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField, FileField
from wtforms.validators import DataRequired, NumberRange
from wtforms import DateField

class TickerForm(FlaskForm):
    ticker = StringField('Ticker Symbol', validators=[DataRequired()])
    submit = SubmitField('Add Ticker')

class StrategyForm(FlaskForm):
    strategy = SelectField('Strategy', choices=[
        ('ma_crossover', 'Moving Average Crossover'),
        ('rsi', 'RSI Strategy')
    ], validators=[DataRequired()])
    param1 = IntegerField('Parameter 1', validators=[DataRequired(), NumberRange(min=1)])
    param2 = IntegerField('Parameter 2', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Configure Strategy')

class BacktestForm(FlaskForm):
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    submit = SubmitField('Run Backtest')

class DataConfigForm(FlaskForm):
    data_interval = SelectField('Data Interval', 
        choices=[('5min', '5 Minutes'), ('15min', '15 Minutes'), ('1h', '1 Hour')],
        default='5min',
        validators=[DataRequired()]
    )
    lookback_period = SelectField('Historical Data Period',
        choices=[('1y', '1 Year'), ('3y', '3 Years'), ('5y', '5 Years')],
        default='5y',
        validators=[DataRequired()]
    )
    submit = SubmitField('Update Data Configuration')
    
class DataSettingsForm(FlaskForm):
    historical_period = SelectField('Historical Data Period', 
        choices=[('5y', '5 Years')],  # Fixed to 5 years per requirements
        default='5y',
        validators=[DataRequired()]
    )
    data_interval = SelectField('Data Interval',
        choices=[('5min', '5 Minutes')],  # Fixed to 5 minutes per requirements
        default='5min',
        validators=[DataRequired()]
    )
    tickers_file = FileField('Upload Tickers CSV')
    submit = SubmitField('Update Data Settings')
