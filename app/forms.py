from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField , DateField , SelectField , ValidationError
from wtforms.validators import DataRequired, Email, Length
from flask_wtf.file import FileField, FileRequired, FileAllowed
from app.models import User

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class UploadResearchMaterialForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    publication_date = DateField('Publication Date', validators=[DataRequired()])
    file = FileField('Research Material', validators=[FileRequired(), FileAllowed(['pdf'], 'PDF files only')])
    submit = SubmitField('Upload')

class CreateProjectForm(FlaskForm):
    name = StringField('Project Name', validators=[DataRequired()])
    description = StringField('Description')
    submit = SubmitField('Create Project')


class InviteUserForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=[('member', 'Member'), ('admin', 'Admin')], validators=[DataRequired()])
    submit = SubmitField('Invite')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if not user:
            raise ValidationError('User with the provided email does not exist.')