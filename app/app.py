from flask import Flask, redirect, url_for, flash, render_template, request, send_from_directory, abort
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import io
from flask import send_file, abort, current_app
import uuid

from .config import Config
from .extensions import db
from .models import (
    Researcher, ResearchPaper, Dataset, Publication, Project, 
    Collaboration, Reviewer, FundingSource
)
from .forms import (
    ResearcherRegistrationForm, LoginForm, ResearchPaperForm,
    DatasetForm, ProjectForm, CollaborationForm, ReviewForm,
    FundingSourceForm, PublicationForm
)



migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return Researcher.query.get(int(user_id))
        except Exception as e:
            print(f"Error loading user: {e}")
            return None

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
            
        form = ResearcherRegistrationForm()
        if form.validate_on_submit():
            email = form.email.data.strip()
            try:
                hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
                researcher = Researcher(
                    email=email,
                    password=hashed_password,
                    f_name=form.f_name.data,
                    l_name=form.l_name.data,
                    expertise=form.expertise.data,
                    affiliation=form.affiliation.data
                )
                db.session.add(researcher)
                db.session.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash('Registration failed. Please try again.', 'danger')

        # Debugging: Print form errors
        if form.errors:
            print("Form errors:", form.errors)

        return render_template('register.html', form=form)


    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
            
        form = LoginForm()
        if form.validate_on_submit():
            try:
                researcher = Researcher.query.filter_by(email=form.email.data.strip()).first()
                
                if researcher and check_password_hash(researcher.password, form.password.data):
                    login_user(researcher)
                    flash('Login successful!', 'success')
                    next_page = request.args.get('next')
                    if not next_page or not next_page.startswith('/'):
                        next_page = url_for('index')
                    return redirect(next_page)
                else:
                    flash('Invalid email or password.', 'danger')
            except Exception as e:
                flash('An error occurred during login. Please try again.', 'danger')
        
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'success')
        return redirect(url_for('home'))

    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/index')
    @login_required
    def index():
        return render_template('index.html', user=current_user)

    @app.route('/papers/create', methods=['GET', 'POST'])
    @login_required
    def create_paper():
        form = ResearchPaperForm()
        if form.validate_on_submit():
            print("Form is valid, processing the submission.")
            
            # Read the uploaded file
            file = form.file.data
            
            # Check if a file was uploaded
            if file:
                file_data = file.read()  # Read the file content
                print(f"File uploaded successfully. Size: {len(file_data)} bytes")

                # Creating a new ResearchPaper instance
                paper = ResearchPaper(
                    title=form.title.data,
                    email=form.email.data,  # Ensure you're capturing the email from the form
                    paperid=str(uuid.uuid4()),  # Auto-generate a unique paper ID
                    publication_place=form.publication_place.data,
                    abstract=form.abstract.data,
                    keywords=form.keywords.data,
                    file=file_data,  # Store the file content directly in the database
                    researcher_id=current_user.id  # Associate the paper with the logged-in researcher
                )
                
                print(f"ResearchPaper object created: {paper.title}, {paper.paperid}")

                try:
                    db.session.add(paper)
                    db.session.commit()
                    print("Paper uploaded and saved to the database successfully.")
                    flash('Paper uploaded successfully!', 'success')
                    return redirect(url_for('view_papers'))
                except Exception as e:
                    db.session.rollback()  # Rollback in case of an error
                    print(f"Error occurred while saving paper to the database: {e}")
                    flash('An error occurred while uploading the paper. Please try again.', 'danger')
            else:
                print("No file was uploaded.")
                flash('Please upload a file.', 'warning')
        else:
            print("Form submission was not valid.")
            # Print specific validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    print(f"Error in {field}: {error}")
            flash('There was an error with your submission. Please correct the fields and try again.', 'danger')
            
        # If form is not valid or file is not uploaded, show the form again
        return render_template('papers/create.html', form=form)




    @app.route('/papers/download/<int:paper_id>', methods=['GET'])
    @login_required
    def download_paper(paper_id):
        # Fetch the paper from the database
        paper = ResearchPaper.query.get(paper_id)
        if paper is None:
            abort(404)  # Paper not found

        # Create a response to send the file data
        return send_file(
            io.BytesIO(paper.file),
            as_attachment=True,
            download_name=paper.title + '.pdf',  # Provide a name for the download
            mimetype='application/pdf'  # Correct MIME type for PDF files
    )


    @app.route('/papers')
    @login_required
    def view_papers():
        papers = ResearchPaper.query.all()
        return render_template('papers/list.html', papers=papers)

    app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64 MB

    @app.route('/datasets/create', methods=['GET', 'POST'])
    @login_required
    def create_dataset():
        form = DatasetForm()
        if form.validate_on_submit():
            file = form.file.data
            if file:
                # Read file data
                file_data = file.read()  # Read the content of the file
                file_size = len(file_data)

                # Log the file size for debugging
                print(f"File size: {file_size} bytes")

                # Check if the file size exceeds a certain limit (e.g., 16 MB for MEDIUMBLOB)
                if file_size > 16 * 1024 * 1024:  # 16 MB
                    flash('File size exceeds the maximum limit of 16 MB.', 'error')
                    return redirect(url_for('create_dataset'))
                # Create a new Dataset instance
                new_dataset = Dataset(
                    name=form.name.data,
                    description=form.description.data,
                    file_data=file_data  # Store file data directly in the database
                )
                db.session.add(new_dataset)
                db.session.commit()

                flash('Dataset uploaded successfully!', 'success')
                return redirect(url_for('view_datasets'))
            else:
                flash('Please upload a file.', 'danger')

        return render_template('datasets/create.html', form=form)



    @app.route('/datasets/download/<int:dataset_id>', methods=['GET'])
    @login_required
    def download_dataset(dataset_id):
        # Fetch the dataset from the database
        dataset = Dataset.query.get(dataset_id)
        if dataset is None:
            abort(404)  # Dataset not found

        # Create a temporary file to send the dataset
        try:
            return send_file(
                io.BytesIO(dataset.file_data),
                as_attachment=True,
                download_name=f"{dataset.name}.csv",  # Provide a name for the download
                mimetype='text/csv'  # Correct MIME type
            )
        except Exception as e:
            abort(500)  # Handle unexpected errors


    @app.route('/datasets')
    @login_required
    def view_datasets():
        datasets = Dataset.query.all()  # Get all datasets from the database
        return render_template('datasets/list.html', datasets=datasets)

    @app.route('/projects/create', methods=['GET', 'POST'])
    @login_required
    def create_project():
        form = ProjectForm()
        if form.validate_on_submit():
            project = Project(
                name=form.name.data,
                description=form.description.data,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                duration=form.duration.data,  # Ensure duration is handled
                creator_id=current_user.id  # Associate the project with the logged-in researcher
            )
            db.session.add(project)
            db.session.commit()
            flash('Project created successfully!', 'success')
            return redirect(url_for('view_projects'))
        return render_template('projects/create.html', form=form)


    @app.route('/projects')
    @login_required
    def view_projects():
        projects = Project.query.all()
        return render_template('projects/list.html', projects=projects)

    @app.route('/projects/<int:project_id>')
    @login_required
    def project_details(project_id):
        project = Project.query.get_or_404(project_id)
        return render_template('projects/details.html', project=project)

    # Review Routes
    @app.route('/papers/<int:paper_id>/review', methods=['GET', 'POST'])
    @login_required
    def add_review(paper_id):
        form = ReviewForm()
        if form.validate_on_submit():
            review = Reviewer(
                paper_id=paper_id,
                researcher_id=current_user.id,
                comments=form.comments.data
            )
            db.session.add(review)
            db.session.commit()
            flash('Review submitted successfully!', 'success')
            return redirect(url_for('view_papers'))
        return render_template('reviews/create.html', form=form, paper_id=paper_id)

    # Funding Routes
    @app.route('/funding/create', methods=['GET', 'POST'])
    @login_required
    def create_funding():
        form = FundingSourceForm()
        if form.validate_on_submit():
            funding = FundingSource(
                name=form.name.data,
                organization=form.organization.data
            )
            db.session.add(funding)
            db.session.commit()
            flash('Funding source added successfully!', 'success')
            return redirect(url_for('view_funding'))
        return render_template('funding/create.html', form=form)

    @app.route('/funding')
    @login_required
    def view_funding():
        funding_sources = FundingSource.query.all()
        return render_template('funding/list.html', funding_sources=funding_sources)

    @app.route('/publications')
    @login_required
    def view_publications():
        publications = Publication.query.all()
        return render_template('publications/list.html', publications=publications)

    # Collaboration routes
    @app.route('/projects/<int:project_id>/collaborate', methods=['GET', 'POST'])
    @login_required
    def collaborate(project_id):
        form = CollaborationForm()
        if form.validate_on_submit():
            collaboration = Collaboration(
                project_id=project_id,
                researcher_id=current_user.id,
                role=form.role.data,
                join_date=datetime.now(),  # Set current date as join date
                collaboration_id=form.collaboration_id.data  # Use form field or generate
            )
            db.session.add(collaboration)
            db.session.commit()
            flash('Collaboration created successfully!', 'success')
            return redirect(url_for('project_details', project_id=project_id))
        
        return render_template('collaborations/add.html', form=form, project_id=project_id)
    
    @app.route('/projects/<int:project_id>/collaborations')
    @login_required
    def view_collaborations(project_id):
        collaborations = Collaboration.query.filter_by(project_id=project_id).all()
        return render_template('collaborations/list.html', collaborations=collaborations)
    return app
