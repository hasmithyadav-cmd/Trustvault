from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class RegisterForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=10, max=128)])
    confirm_password = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Create account")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign in")

class UploadForm(FlaskForm):
    file = FileField("Choose a document", validators=[FileRequired()])
    submit = SubmitField("Upload document")

class ShareForm(FlaskForm):
    user_id = SelectField("Share with", coerce=int, validators=[DataRequired()])
    can_download = BooleanField("Allow downloading")
    submit = SubmitField("Share document")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from models import User
        from extensions import db
        from sqlalchemy import select
        self.user_id.choices = [(u.id, f"{u.name} ({u.email})")
                                for u in db.session.scalars(select(User).order_by(User.email)).all()]
