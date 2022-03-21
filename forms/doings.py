from flask_wtf import FlaskForm
from wtforms import StringField, RadioField
from wtforms import SubmitField
from wtforms.validators import DataRequired


class DoingsForm(FlaskForm):
    content = StringField('Дело', validators=[DataRequired()])
    doing_category = RadioField('Категория', choices=[(0, 'Домашнее'), (1, 'Рабочее')], default=0)
    submit = SubmitField('Добавить')