from .extensions import db
from flask_login import UserMixin
from datetime import datetime
import uuid
from sqlalchemy import func

# Association Tables
authored = db.Table('authored',
    db.Column('researcher_id', db.Integer, db.ForeignKey('researcher.id')),
    db.Column('paper_id', db.Integer, db.ForeignKey('research_paper.id'))
)

has_dataset = db.Table('has_dataset',
    db.Column('paper_id', db.Integer, db.ForeignKey('research_paper.id')),
    db.Column('dataset_id', db.Integer, db.ForeignKey('dataset.id'))
)

cites = db.Table('cites',
    db.Column('paper_id', db.Integer, db.ForeignKey('research_paper.id')),
    db.Column('publication_id', db.Integer, db.ForeignKey('publication.id'))
)

reviews = db.Table('reviews',
    db.Column('reviewer_id', db.Integer, db.ForeignKey('reviewer.id')),
    db.Column('paper_id', db.Integer, db.ForeignKey('research_paper.id'))
)

project_funding = db.Table('project_funding',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id')),
    db.Column('funding_source_id', db.Integer, db.ForeignKey('funding_source.id'))
)

class Researcher(db.Model, UserMixin):
    __tablename__ = 'researcher'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(300), nullable=False)
    f_name = db.Column(db.String(50))
    l_name = db.Column(db.String(50))
    expertise = db.Column(db.String(200))
    affiliation = db.Column(db.String(200))

    # Relationships
    authored_papers = db.relationship('ResearchPaper', secondary=authored, back_populates='authors')
    collaborations = db.relationship('Collaboration', back_populates='researcher')

class ResearchPaper(db.Model):
    __tablename__ = 'research_paper'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    paperid = db.Column(db.String(50), unique=True,default=lambda: str(uuid.uuid4()))
    publication_place = db.Column(db.String(200))
    abstract = db.Column(db.Text)
    keywords = db.Column(db.String(500))
    file = db.Column(db.LargeBinary(length=2**24))

    # Foreign key relationship to the Researcher model
    researcher_id = db.Column(db.Integer, db.ForeignKey('researcher.id'))
    
    # Relationships
    researcher = db.relationship('Researcher', back_populates='authored_papers')
    datasets = db.relationship('Dataset', secondary='has_dataset')
    citations = db.relationship('Publication', secondary='cites')
    authors = db.relationship('Researcher', secondary='authored', back_populates='authored_papers')

class Dataset(db.Model):
    __tablename__ = 'dataset'  # Make sure this is set if not defined elsewhere
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_data = db.Column(db.LargeBinary)  # Store the file as binary data

    def __repr__(self):
        return f'<Dataset {self.name}>'

class Publication(db.Model):
    __tablename__ = 'publication'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    publication_venue_id = db.Column(db.String(50))
    type = db.Column(db.String(50))  # 'Journal' or 'Conference'

class Project(db.Model):
    __tablename__ = 'project'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    project_id = db.Column(db.String(50), unique=True)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    duration = db.Column(db.Integer)  # in months
    creator_id = db.Column(db.Integer, db.ForeignKey('researcher.id'))  # New field for project creator

    # Relationships
    creator = db.relationship('Researcher', backref='projects_created')
    collaborations = db.relationship('Collaboration', back_populates='project')  # Add this line

class Collaboration(db.Model):
    __tablename__ = 'collaboration'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    researcher_id = db.Column(db.Integer, db.ForeignKey('researcher.id'))
    role = db.Column(db.String(50))
    join_date = db.Column(db.Date)
    collaboration_id = db.Column(db.String(50), unique=True)
    
    # Relationships
    project = db.relationship('Project', back_populates='collaborations')
    researcher = db.relationship('Researcher', back_populates='collaborations')

class Reviewer(db.Model):
    __tablename__ = 'reviewer'
    
    id = db.Column(db.Integer, primary_key=True)
    reviewer_id = db.Column(db.String(50), unique=True)
    f_name = db.Column(db.String(50))
    l_name = db.Column(db.String(50))
    name = db.Column(db.String(100))
    comments = db.Column(db.Text)

class FundingSource(db.Model):
    __tablename__ = 'funding_source'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    organization = db.Column(db.String(200))
    funding_source_id = db.Column(db.String(50), unique=True)
