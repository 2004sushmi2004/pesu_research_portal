# app/app.py
from flask import Flask, redirect, url_for, flash, render_template
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .config import Config  # Assuming Config has all necessary keys
from .extensions import db  # Import db from extensions
from .models import User, ResearchMaterial, Project ,  User# Import models after db initialization
from .forms import RegistrationForm, LoginForm , UploadResearchMaterialForm , CreateProjectForm , InviteUserForm
from werkzeug.utils import secure_filename
import os
from flask import send_from_directory


migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)  # Load configurations from Config

    # Initialize the database, migration, and login manager
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Redirect to login if not authenticated
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id):
        """Load user from the database by user_id."""
        return User.query.get(int(user_id))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """Handle user registration."""
        form = RegistrationForm()
        if form.validate_on_submit():
            hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
            user = User(email=form.email.data, password=hashed_password)
            try:
                db.session.add(user)
                db.session.commit()
                flash('You have successfully registered. Please log in.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback() # Rollback the session in case of error
                print(f"Error occurred during registration: {e}")  # Print error message
                flash('Registration failed. Please try again.', 'danger')
        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Handle user login."""
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and check_password_hash(user.password, form.password.data):
                login_user(user)
                flash('You have been logged in.', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid email or password.', 'danger')
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        """Handle user logout."""
        logout_user()
        flash('You have been logged out.', 'success')
        return redirect(url_for('home'))  # Redirect to home after logout

    @app.route('/index')
    @login_required
    def index():
        """Home page after login."""
        return render_template('index.html', user=current_user)

    @app.route('/')
    def home():
        """Render a public homepage."""
        return render_template('home.html')
    


    @app.route('/upload', methods=['GET', 'POST'])
    @login_required
    def upload_research_material():
        form = UploadResearchMaterialForm()
        if form.validate_on_submit():
            file = form.file.data
            filename = secure_filename(file.filename)
            file_path = os.path.join('static', 'uploads', filename)
            file.save(file_path)

            research_material = ResearchMaterial(
                title=form.title.data,
                author=form.author.data,
                publication_date=form.publication_date.data,
                file_path=file_path
            )
            db.session.add(research_material)
            db.session.commit()
            flash('Research material uploaded successfully.', 'success')
            return redirect(url_for('index'))
        return render_template('upload.html', form=form)
    
    @app.route('/materials')
    def research_materials():
        materials = ResearchMaterial.query.all()
        return render_template('materials.html', materials=materials)
    
    @app.route('/materials/<int:material_id>/download')
    @login_required
    def download_research_material(material_id):
        material = ResearchMaterial.query.get_or_404(material_id)
        return send_from_directory('static/uploads', material.file_path, as_attachment=True)
    
  

    @app.route('/projects/create', methods=['GET', 'POST'])
    @login_required
    def create_project():
        form = CreateProjectForm()
        if form.validate_on_submit():
            project = Project(
                name=form.name.data,
                description=form.description.data
            )
            db.session.add(project)
            db.session.commit()
            flash('Project created successfully.', 'success')
            return redirect(url_for('projects'))
        return render_template('create_project.html', form=form)
    
    @app.route('/projects', methods=['GET'])
    @login_required
    def projects():
        """List all projects."""
        try:
            projects = Project.query.all()  # Fetch all projects from the database
            return render_template('projects.html', projects=projects)
        except Exception as e:
            print(f"Error fetching projects: {e}")  # Debug output
            return "Error fetching projects", 500


    
    @app.route('/projects/<int:project_id>')
    @login_required
    def project_details(project_id):
        project = Project.query.get_or_404(project_id)
        return render_template('project_details.html', project=project)
    
 

    @app.route('/projects/<int:project_id>/invite', methods=['POST'])
    @login_required
    def invite_user(project_id):
        project = Project.query.get_or_404(project_id)
        form = InviteUserForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            project.users.append(user)
            user.role = form.role.data
            db.session.commit()
            flash('User invited to the project.', 'success')
        return redirect(url_for('project_details', project_id=project.id))

    return app

    

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()  # Ensure tables are created
    app.run(debug=True)
