from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, FloatField
from wtforms.validators import DataRequired, URL, Email, EqualTo


class CreateProductForm(FlaskForm):
    title = StringField("Product title", validators=[DataRequired()], render_kw={"autofocus": True, "autocomplete": 'off'})
    description = StringField("Product description", validators=[DataRequired()], render_kw={"autocomplete": 'off'})
    price = FloatField("Price (£)", validators=[DataRequired()])
    img_url = StringField("Image URL", validators=[DataRequired(), URL()])
    submit = SubmitField("Add product")


class CreateCustomerForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()], render_kw={"autofocus": True, "autocomplete": 'off'})
    email = StringField("Email", validators=[DataRequired(), Email()], render_kw={"autocomplete": 'off'})
    password = PasswordField("Password", validators=[DataRequired(), EqualTo('confirm', message='Passwords must match')])
    # TODO Add password confirmation field
    confirm = PasswordField("Repeat Password")
    submit = SubmitField("Register")


class LogInForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()], render_kw={"autofocus": True, "autocomplete": 'off'})
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")

