from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, FloatField
from wtforms.validators import DataRequired, URL, Email


class CreateProductForm(FlaskForm):
    description = StringField("Product description", validators=[DataRequired()])
    price = FloatField("Price (£)", validators=[DataRequired()])
    img_url = StringField("Image URL", validators=[DataRequired(), URL()])
    submit = SubmitField("Add product")


class CreateCustomerForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()], render_kw={"autofocus": True, "autocomplete": 'off'})
    email = StringField("Email", validators=[DataRequired(), Email()], render_kw={"autocomplete": 'off'})
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Register")


class LogInForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()], render_kw={"autofocus": True, "autocomplete": 'off'})
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")

