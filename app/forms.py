from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, DateField, SelectField, 
    TextAreaField, ValidationError, MultipleFileField,SelectMultipleField,
)
from wtforms.validators import DataRequired, Email, Length, Optional
from flask_wtf.file import FileField, FileRequired, FileAllowed
from .models import Researcher


class ResearchPaperForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    publication_place = StringField('Publication Place')
    abstract = TextAreaField('Abstract')
    keywords = StringField('Keywords')
    file = FileField('Upload File', validators=[DataRequired()])
    dataset_ids = SelectMultipleField('Select Datasets', choices=[], coerce=int)  # Add this line
    submit = SubmitField('Submit')


class ResearcherRegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    f_name = StringField('First Name', validators=[DataRequired()])
    l_name = StringField('Last Name', validators=[DataRequired()])
    expertise = StringField('Area of Expertise', validators=[DataRequired()])
    affiliation = StringField('Institution/Organization', validators=[DataRequired()])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class ResearchPaperForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    publication_place = StringField('Publication Place')
    abstract = TextAreaField('Abstract')
    keywords = StringField('Keywords')
    file = FileField('Upload File', validators=[DataRequired()])
    dataset_ids = SelectMultipleField('Select Datasets', choices=[], coerce=int)  # Add this line
    submit = SubmitField('Submit')


class DatasetForm(FlaskForm):
    name = StringField('Dataset Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    file = FileField('Upload File', validators=[DataRequired()])  # FileField for file uploads
    submit = SubmitField('Upload Dataset')



class ProjectForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    name = StringField('Project Name', validators=[DataRequired()])
    description = TextAreaField('Project Description', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    submit = SubmitField('Create Project')

class CollaborationForm(FlaskForm):
    researcher_email = StringField('Researcher Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=[
        ('PI', 'Principal Investigator'),
        ('Co-PI', 'Co-Principal Investigator'),
        ('Researcher', 'Researcher'),
        ('Assistant', 'Research Assistant')
    ], validators=[DataRequired()])
    submit = SubmitField('Add Collaborator')

    def validate_researcher_email(self, email):
        researcher = Researcher.query.filter_by(email=email.data).first()
        if not researcher:
            raise ValidationError('No researcher found with this email address.')

class ReviewForm(FlaskForm):
    comments = TextAreaField('Review Comments', validators=[DataRequired()])
    submit = SubmitField('Submit Review')

class FundingSourceForm(FlaskForm):
    name = StringField('Funding Source Name', validators=[DataRequired()])
    organization = StringField('Organization', validators=[DataRequired()])
    submit = SubmitField('Add Funding Source')

class PublicationForm(FlaskForm):
    name = StringField('Publication Name', validators=[DataRequired()])
    publication_venue_id = StringField('Publication Venue ID', validators=[DataRequired()])
    type = SelectField('Publication Type', choices=[
        ('Journal', 'Journal'),
        ('Conference', 'Conference')
    ], validators=[DataRequired()])
    submit = SubmitField('Add Publication')