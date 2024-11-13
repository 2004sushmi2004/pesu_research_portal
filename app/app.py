from flask import Flask, redirect, url_for, flash, render_template, request, send_file, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
import io
import uuid
from datetime import datetime
import os
from flask import session

class User:
    def __init__(self, id, email, user_type):
        self.id = id
        self.email = email
        self.user_type = user_type
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return str(self.id)
    
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Unlock@2004",
            database="pesu_research_portal"
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id):
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # First, try to load a researcher with the given user_id
            cursor.execute("SELECT * FROM researcher WHERE researcher_id = %s", (user_id,))
            user_data = cursor.fetchone()
            
            # If no researcher is found, try to load a funding_source with the given user_id
            if not user_data:
                cursor.execute("SELECT * FROM funding_source WHERE funding_source_id = %s", (user_id,))
                user_data = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if user_data:
                # Return a User object based on the user type
                return User(user_data['researcher_id'] if 'researcher_id' in user_data else user_data['funding_source_id'], 
                            user_data['email'], 
                            user_data['user_type'])
            return None
        except Error as e:
            print(f"Error loading user: {e}")
            return None
        
    @app.route('/')
    def landing():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        return redirect(url_for('login'))

    @app.route('/home')
    @login_required
    def home():
        try:
            conn = get_db_connection()
            if not conn:
                flash("Unable to connect to database", "error")
                return render_template('home.html', stats=None)
                
            cursor = conn.cursor(dictionary=True)
            
            # First verify if tables exist
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM information_schema.tables 
                WHERE TABLE_SCHEMA = 'pesu_research_portal' 
                AND TABLE_NAME IN ('project', 'research_paper', 'dataset')
            """)
            existing_tables = [row['TABLE_NAME'] for row in cursor.fetchall()]
            
            # Build dynamic query based on existing tables
            queries = []
            if 'project' in existing_tables:
                queries.append("(SELECT COUNT(*) FROM project) as total_projects")
            if 'research_paper' in existing_tables:
                queries.append("(SELECT COUNT(*) FROM research_paper) as total_papers")
            if 'dataset' in existing_tables:
                queries.append("(SELECT COUNT(*) FROM dataset) as total_datasets")
                
            if queries:
                query = "SELECT " + ", ".join(queries)
                cursor.execute(query)
                stats = cursor.fetchone()
            else:
                stats = {'total_projects': 0, 'total_papers': 0, 'total_datasets': 0}
                
            cursor.close()
            conn.close()
            
            return render_template('home.html', stats=stats)
            
        except Error as e:
            print(f"Database error: {e}")
            flash("An error occurred while fetching statistics", "error")
            return render_template('home.html', stats=None)
        except Exception as e:
            print(f"Unexpected error: {e}")
            flash("An unexpected error occurred", "error")
            return render_template('home.html', stats=None)
        
    @app.route('/register', methods=['GET'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        
        user_type = request.args.get('type', 'researcher')
        if user_type not in ['researcher', 'funding_source']:
            user_type = 'researcher'
        
        return render_template('register_choice.html')

    @app.route('/register/researcher', methods=['GET', 'POST'])
    def register_researcher():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
            
        if request.method == 'POST':
            # Get form data
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            f_name = request.form.get('f_name', '').strip()
            l_name = request.form.get('l_name', '').strip()
            expertise = request.form.get('expertise', '').strip()
            affiliation = request.form.get('affiliation', '').strip()

            # Basic validation
            errors = []
            if not email or '@' not in email:
                errors.append('Valid email is required')
            if not password:
                errors.append('Password is required')
            if password != confirm_password:
                errors.append('Passwords do not match')
            if not f_name:
                errors.append('First name is required')
            if not l_name:
                errors.append('Last name is required')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template('register_researcher.html')

            try:
                conn = get_db_connection()
                if not conn:
                    flash('Database connection failed', 'danger')
                    return render_template('register_researcher.html')

                cursor = conn.cursor()
                
                # Check if email already exists
                cursor.execute("SELECT email FROM researcher WHERE email = %s", (email,))
                if cursor.fetchone():
                    flash('Email already registered', 'danger')
                    return render_template('register_researcher.html')

                # Generate unique researcher_id and hash password
                researcher_id = str(uuid.uuid4())
                hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
                
                # Insert new researcher
                insert_query = """
                    INSERT INTO researcher 
                    (researcher_id, email, password, f_name, l_name, expertise, affiliation,user_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s,%s)
                """
                values = (
                    researcher_id,
                    email,
                    hashed_password,
                    f_name,
                    l_name,
                    expertise,
                    affiliation,
                    'researcher'
                )
                
                cursor.execute(insert_query, values)
                conn.commit()
                
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))

            except Error as e:
                flash(f'Registration failed: {str(e)}', 'danger')
                return render_template('register_researcher.html')
                
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()
        
        return render_template('register_researcher.html')
    
    @app.route('/register/funding_source', methods=['GET', 'POST'])
    def register_funding_source():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
            
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            name = request.form.get('name', '').strip()
            organization = request.form.get('organization', '').strip()
            contact_person = request.form.get('contact_person', '').strip()
            phone = request.form.get('phone', '').strip()

            errors = []
            if not email or '@' not in email:
                errors.append('Valid email is required')
            if not password:
                errors.append('Password is required')
            if password != confirm_password:
                errors.append('Passwords do not match')
            if not name:
                errors.append('Name is required')
            if not organization:
                errors.append('Organization is required')
            if not contact_person:
                errors.append('Contact person is required')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template('register_funding_source.html')

            try:
                conn = get_db_connection()
                if not conn:
                    flash('Database connection failed', 'danger')
                    return render_template('register_funding_source.html')

                cursor = conn.cursor()
                
                # Check if email already exists
                cursor.execute("SELECT email FROM funding_source WHERE email = %s", (email,))
                if cursor.fetchone():
                    flash('Email already registered', 'danger')
                    return render_template('register_funding_source.html')

                funding_source_id = str(uuid.uuid4())
                hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
                
                insert_query = """
                    INSERT INTO funding_source 
                    (funding_source_id, email, password, name, organization, contact_person, phone,user_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s,%s)
                """
                values = (
                    funding_source_id,
                    email,
                    hashed_password,
                    name,
                    organization,
                    contact_person,
                    phone,
                    'funding_source'
                )
                
                cursor.execute(insert_query, values)
                conn.commit()
                
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))

            except Error as e:
                flash(f'Registration failed: {str(e)}', 'danger')
                return render_template('register_funding_source.html')
                
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()
        
        return render_template('register_funding_source.html')
    


    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('home'))

        # Get the next parameter from either GET or POST request
        next_page = request.args.get('next') or request.form.get('next')
        
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            user_type = request.form.get('user_type')

            if not email or not password or not user_type:
                flash('Please enter all required fields', 'danger')
                return render_template('login.html', next=next_page)

            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)

                if user_type == 'researcher':
                    cursor.execute("SELECT * FROM researcher WHERE email = %s", (email,))
                    user_data = cursor.fetchone()
                    if user_data and check_password_hash(user_data['password'], password):
                        user = User(user_data['researcher_id'], user_data['email'], 'researcher')
                        login_user(user)
                        session.permanent = True  # Make session permanent
                        return redirect(next_page or url_for('home'))

                elif user_type == 'funding_source':
                    cursor.execute("SELECT * FROM funding_source WHERE email = %s", (email,))
                    user_data = cursor.fetchone()
                    if user_data and check_password_hash(user_data['password'], password):
                        user = User(user_data['funding_source_id'], user_data['email'], 'funding_source')
                        login_user(user)
                        session.permanent = True  # Make session permanent
                        return redirect(url_for('browse_projects_funder'))
                
                flash('Invalid email or password', 'danger')

            except Error as e:
                flash(f'Login failed: {str(e)}', 'danger')
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()

        # For GET requests or failed logins, render the template with next parameter
        return render_template('login.html', next=next_page)



    
    @app.route('/browse_projects_funder')
    @login_required
    def browse_projects_funder():
        if current_user.user_type != 'funding_source':
            flash('Access denied', 'danger')
            return redirect(url_for('home'))
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT p.*, r.f_name, r.l_name, r.affiliation 
                FROM project p 
                JOIN researcher r ON p.creator_id = r.researcher_id
                WHERE p.project_id NOT IN (
                    SELECT project_id FROM funded_projects 
                    WHERE funding_source_id = %s AND status = 'approved'
                )
            """, (current_user.id,))
            projects = cursor.fetchall()
            return render_template('browse_projects_funder.html', projects=projects)
        finally:
            cursor.close()
            conn.close()

    # Route for funding a project
    @app.route('/fund_project/<project_id>', methods=['GET', 'POST'])
    @login_required
    def fund_project(project_id):
        if current_user.user_type != 'funding_source':
            flash('Access denied', 'danger')
            return redirect(url_for('home'))
        
        if request.method == 'POST':
            amount = request.form.get('amount')
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                funding_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO funded_projects 
                    (funding_id, project_id, funding_source_id, amount, funding_date, status)
                    VALUES (%s, %s, %s, %s, CURDATE(), 'approved')
                """, (funding_id, project_id, current_user.id, amount))
                conn.commit()
                flash('Project funded successfully!', 'success')
                return redirect(url_for('browse_projects_funder'))
            except Error as e:
                flash(f'Funding failed: {str(e)}', 'danger')
            finally:
                cursor.close()
                conn.close()
        
        return render_template('fund_project.html', project_id=project_id)


    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/logout')
    def logout():
        logout_user()
        flash('You have been logged out successfully.', 'info')
        return redirect(url_for('login'))

    @app.route('/upload_paper', methods=['GET', 'POST'])
    @login_required
    def upload_paper():
        if request.method == 'POST':
            # Get form data
            title = request.form.get('title', '').strip()
            authors = request.form.get('authors', '').strip()
            abstract = request.form.get('abstract', '').strip()
            publication_date = request.form.get('publication_date', '').strip()
            publication_venueid = request.form.get('publication_venueid', '').strip()
            keywords = request.form.get('keywords', '').strip()
            paper_file = request.files['paper_file']

            

            try:
                conn = get_db_connection()
                if not conn:
                    flash('Database connection failed', 'danger')
                    return render_template('upload_paper.html')

                cursor = conn.cursor()

                # Get paper ID from database function
                cursor.execute("SELECT generate_paper_id()")
                paperid = cursor.fetchone()[0]

                # Insert new research paper
                insert_query = """
                    INSERT INTO research_paper
                    (paperid, title, authors, abstract, publication_date, publication_venueid, file, researcher_id, keywords)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (
                    paperid,
                    title,
                    authors,
                    abstract,
                    publication_date,
                    publication_venueid,
                    paper_file.read(),
                    current_user.id,
                    keywords
                )

                cursor.execute(insert_query, values)
                conn.commit()

                flash('Paper uploaded successfully!', 'success')
                return redirect(url_for('home'))

            except Error as e:
                flash(f'Failed to upload paper: {str(e)}', 'danger')
                return render_template('upload_paper.html')

            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()

        return render_template('upload_paper.html')
    @app.route('/delete_paper/<paperid>', methods=['POST'])
    @login_required
    def delete_paper(paperid):
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'danger')
                return redirect(url_for('my_papers'))

            cursor = conn.cursor()
            cursor.execute("DELETE FROM research_paper WHERE paperid = %s AND researcher_id = %s", (paperid, current_user.id))
            conn.commit()

            flash('Paper deleted successfully', 'success')
            return redirect(url_for('my_papers'))

        except Error as e:
            flash(f'Failed to delete paper: It has already been reviewed', 'danger')
            return redirect(url_for('my_papers'))

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    
    @app.route('/my_papers')
    @login_required
    def my_papers():
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'danger')
                return redirect(url_for('dashboard'))

            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM research_paper WHERE researcher_id = %s", (current_user.id,))
            my_papers = cursor.fetchall()

            return render_template('my_papers.html', papers=my_papers)

        except Error as e:
            flash(f'Failed to retrieve papers: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    @app.route('/browse_papers')
    def browse_papers():
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'danger')
                return redirect(url_for('dashboard'))

            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM research_paper")
            all_papers = cursor.fetchall()

            return render_template('browse_papers.html', papers=all_papers)

        except Error as e:
            flash(f'Failed to retrieve papers: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    def increment_paper_downloads(paperid):
    
        try:
            conn = get_db_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE research_paper 
                SET downloads = downloads + 1 
                WHERE paperid = %s
            """, (paperid,))
            conn.commit()
            return True
            
        except Error as e:
            print(f"Error incrementing downloads: {e}")
            return False
            
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    


    @app.route('/download_paper/<paperid>')
    @login_required
    def download_paper(paperid):
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'danger')
                return redirect(url_for('dashboard'))

            cursor = conn.cursor()
            cursor.execute("SELECT file, title FROM research_paper WHERE paperid = %s", (paperid,))
            paper_data = cursor.fetchone()

            if paper_data:
                # Increment download counter
                success = increment_paper_downloads(paperid)
                if not success:
                    flash('Failed to update download counter', 'warning')
                    
                file_data = paper_data[0]
                file_name = f"{paper_data[1]}.pdf"
                return send_file(
                    io.BytesIO(file_data), 
                    mimetype='application/pdf', 
                    as_attachment=True, 
                    download_name=file_name
                )
            else:
                flash('Paper not found', 'danger')
                return redirect(url_for('my_papers'))

        except Error as e:
            flash(f'Failed to download paper: {str(e)}', 'danger')
            return redirect(url_for('my_papers'))

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    
    @app.route('/upload_dataset', methods=['GET', 'POST'])
    @login_required
    def upload_dataset():
        if request.method == 'POST':
            # Get form data
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            dataset_file = request.files['dataset_file']

            # Generate unique dataset_id
            dataset_id = str(uuid.uuid4())

            try:
                conn = get_db_connection()
                if not conn:
                    flash('Database connection failed', 'danger')
                    return render_template('upload_dataset.html')

                cursor = conn.cursor()

                # Insert new dataset, including researcher_id
                insert_query = """
                    INSERT INTO dataset
                    (dataset_id, name, description, meta_data, file, researcher_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                values = (
                    dataset_id,
                    name,
                    description,
                    '',  # You can add metadata if needed
                    dataset_file.read(),
                    current_user.id  # Add the researcher_id
                )

                cursor.execute(insert_query, values)
                conn.commit()

                flash('Dataset uploaded successfully!', 'success')
                return redirect(url_for('home'))

            except Error as e:
                flash(f'Failed to upload dataset: {str(e)}', 'danger')
                return render_template('upload_dataset.html')

            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()

        return render_template('upload_dataset.html')



    @app.route('/download_dataset/<dataset_id>')
    @login_required
    def download_dataset(dataset_id):
        try:
            print("Entering download_dataset() function")
            conn = get_db_connection()
            if not conn:
                print("Database connection failed")
                flash('Database connection failed', 'danger')
                return redirect(url_for('dashboard'))

            cursor = conn.cursor()
            print(f"Executing SQL query to retrieve dataset with ID: {dataset_id}")
            cursor.execute("SELECT name, file FROM dataset WHERE dataset_id = %s", (dataset_id,))
            dataset_data = cursor.fetchone()

            if dataset_data:
                print("Dataset found, preparing download")
                file_data = dataset_data[1]
                file_name = f"{dataset_data[0]}.csv"
                return send_file(io.BytesIO(file_data), mimetype='text/csv', download_name=file_name, as_attachment=True)
            else:
                print("Dataset not found")
                flash('Dataset not found', 'danger')
                return redirect(url_for('my_datasets'))

        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            flash(f'Failed to download dataset: {str(e)}', 'danger')
            return redirect(url_for('my_datasets'))

        finally:
            if 'cursor' in locals():
                cursor.close()
                print("Closed database cursor")
            if 'conn' in locals():
                conn.close()
                print("Closed database connection")


    @app.route('/delete_dataset/<dataset_id>', methods=['POST'])
    @login_required
    def delete_dataset(dataset_id):
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'danger')
                return redirect(url_for('my_datasets'))

            cursor = conn.cursor()
            print(f"Attempting to delete dataset with ID: {dataset_id}")
            cursor.execute("DELETE FROM dataset WHERE dataset_id = %s AND researcher_id = %s", (dataset_id, current_user.id))
            conn.commit()

            flash('Dataset deleted successfully', 'success')
            return redirect(url_for('my_datasets'))

        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            flash(f'Failed to delete dataset: {str(e)}', 'danger')
            return redirect(url_for('my_datasets'))

        finally:
            if 'cursor' in locals():
                cursor.close()
                print("Closed database cursor")
            if 'conn' in locals():
                conn.close()
                print("Closed database connection")


    @app.route('/my_datasets')
    @login_required
    def my_datasets():
        """ Render the 'my_datasets' template, displaying the user's uploaded datasets. """
        try:
            print("Entering my_datasets() function")
            conn = get_db_connection()
            if not conn:
                print("Database connection failed")
                flash('Database connection failed', 'danger')
                return redirect(url_for('dashboard'))
            
            print(f"Current user ID: {current_user.id}")
            cursor = conn.cursor(dictionary=True)
            print("Executing SQL query to retrieve user's datasets")
            cursor.execute("SELECT dataset_id, name, description, file FROM dataset WHERE researcher_id = %s", (current_user.id,))
            my_datasets = cursor.fetchall()
            print(f"Retrieved {len(my_datasets)} datasets for the user")

            if not my_datasets:
                flash("You haven't uploaded any datasets yet.", 'warning')
            
            return render_template('my_datasets.html', datasets=my_datasets)

        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            flash(f'Failed to retrieve user datasets: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))

        finally:
            if 'cursor' in locals():
                cursor.close()
                print("Closed database cursor")
            if 'conn' in locals():
                conn.close()
                print("Closed database connection")


    @app.route('/browse_datasets')
    def browse_datasets():
            try:
                conn = get_db_connection()
                if not conn:
                    flash('Database connection failed', 'danger')
                    return redirect(url_for('dashboard'))

                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM dataset")
                all_datasets = cursor.fetchall()

                return render_template('browse_datasets.html', datasets=all_datasets)

            except Error as e:
                flash(f'Failed to retrieve papers: {str(e)}', 'danger')
                return redirect(url_for('dashboard'))

            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()
    
    @app.route('/create_project', methods=['GET', 'POST'])
    @login_required
    def create_project():
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            start_date = request.form.get('start_date', '').strip()
            end_date = request.form.get('end_date', '').strip()
            
            # Validation
            errors = []
            if not name:
                errors.append('Project name is required')
            if not description:
                errors.append('Project description is required')
            if not start_date:
                errors.append('Start date is required')
                
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template('create_project.html')

            try:
                conn = get_db_connection()
                if not conn:
                    flash('Database connection failed', 'danger')
                    return render_template('create_project.html')

                cursor = conn.cursor()
                
                # Generate unique project_id
                project_id = str(uuid.uuid4())
                
                # Insert new project
                insert_query = """
                    INSERT INTO project 
                    (project_id, name, description, start_date, end_date, creator_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                values = (
                    project_id,
                    name,
                    description,
                    start_date,
                    end_date,
                    current_user.id
                )
                
                cursor.execute(insert_query, values)
                conn.commit()
                
                flash('Project created successfully!', 'success')
                return redirect(url_for('home'))

            except Error as e:
                flash(f'Failed to create project: {str(e)}', 'danger')
                return render_template('create_project.html')
                
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()
        
        return render_template('create_project.html')

    
    @app.route('/my_projects')
    @login_required
    def my_projects():
        if current_user.user_type != 'researcher':
            flash('Access denied', 'danger')
            return redirect(url_for('home'))
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # First get all projects
            cursor.execute("""
                SELECT p.*
                FROM project p
                WHERE p.creator_id = %s
            """, (current_user.id,))
            projects = cursor.fetchall()
            
            # Then get all fundings for these projects
            project_ids = [p['project_id'] for p in projects]
            if project_ids:
                placeholders = ','.join(['%s'] * len(project_ids))
                cursor.execute(f"""
                    SELECT f.*, fs.name as funder_name, f.project_id
                    FROM funded_projects f
                    JOIN funding_source fs ON f.funding_source_id = fs.funding_source_id
                    WHERE f.project_id IN ({placeholders})
                    ORDER BY f.funding_date DESC
                """, tuple(project_ids))
                fundings = cursor.fetchall()
                
                # Group fundings by project_id
                funding_dict = {}
                for funding in fundings:
                    if funding['project_id'] not in funding_dict:
                        funding_dict[funding['project_id']] = []
                    funding_dict[funding['project_id']].append(funding)
                
                # Add fundings to their respective projects
                for project in projects:
                    project['fundings'] = funding_dict.get(project['project_id'], [])
            
            return render_template('my_projects.html', projects=projects)
        finally:
            cursor.close()
            conn.close()


    @app.route('/browse_projects')
    def browse_projects():
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'danger')
                return redirect(url_for('dashboard'))

            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT p.*, r.f_name, r.l_name 
                FROM project p
                JOIN researcher r ON p.creator_id = r.researcher_id
                ORDER BY p.start_date DESC
            """)
            projects = cursor.fetchall()

            return render_template('browse_projects.html', projects=projects)

        except Error as e:
            flash(f'Failed to retrieve projects: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    @app.route('/edit_project/<project_id>', methods=['GET', 'POST'])
    @login_required
    def edit_project(project_id):
        if request.method == 'GET':
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM project WHERE project_id = %s AND creator_id = %s", 
                            (project_id, current_user.id))
                project = cursor.fetchone()
                
                if not project:
                    flash('Project not found or access denied', 'danger')
                    return redirect(url_for('my_projects'))
                    
                return render_template('edit_project.html', project=project)
                
            except Error as e:
                flash(f'Error retrieving project: {str(e)}', 'danger')
                return redirect(url_for('my_projects'))
                
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()
                    
        elif request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            start_date = request.form.get('start_date', '').strip()
            end_date = request.form.get('end_date', '').strip()
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                update_query = """
                    UPDATE project 
                    SET name = %s, description = %s, start_date = %s, end_date = %s
                    WHERE project_id = %s AND creator_id = %s
                """
                cursor.execute(update_query, 
                            (name, description, start_date, end_date, project_id, current_user.id))
                conn.commit()
                
                flash('Project updated successfully', 'success')
                return redirect(url_for('my_projects'))
                
            except Error as e:
                flash(f'Failed to update project: {str(e)}', 'danger')
                return redirect(url_for('edit_project', project_id=project_id))
                
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()

    @app.route('/delete_project/<project_id>', methods=['POST'])
    @login_required
    def delete_project(project_id):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM project WHERE project_id = %s AND creator_id = %s", 
                        (project_id, current_user.id))
            conn.commit()
            
            flash('Project deleted successfully', 'success')
            return redirect(url_for('my_projects'))
            
        except Error as e:
            flash(f'Failed to delete project: It already has collaborators or funding source', 'danger')
            return redirect(url_for('my_projects'))
            
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()



    def validate_researcher_exists(cursor, researcher_id):
        """Validate that a researcher exists in the database"""
        cursor.execute("SELECT researcher_id FROM researcher WHERE researcher_id = %s", (str(researcher_id),))
        return cursor.fetchone() is not None

    def validate_project_exists(cursor, project_id, creator_id):
        """Validate that a project exists and belongs to the creator"""
        cursor.execute("SELECT project_id FROM project WHERE project_id = %s AND creator_id = %s", 
                    (str(project_id), str(creator_id)))
        return cursor.fetchone() is not None

    def check_existing_request(cursor, sender_id, receiver_id, project_id):
        """Check if a collaboration request already exists"""
        cursor.execute("""
            SELECT collaboration_request_id FROM collaboration_request 
            WHERE sender_id = %s AND receiver_id = %s AND project_id = %s 
            AND status = 'pending'
        """, (str(sender_id), str(receiver_id), str(project_id)))
        return cursor.fetchone() is not None

    @app.route('/find_collaborators', methods=['GET', 'POST'])
    @login_required
    def find_collaborators():
        if request.method == 'POST':
            collaborator_id = request.form.get('collaborator_id')
            project_id = request.form.get('project_id')
            
            # Input validation
            if not collaborator_id or not project_id:
                flash('Missing required fields.', 'danger')
                return redirect(url_for('find_collaborators'))
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                
                # Validate the receiver exists
                if not validate_researcher_exists(cursor, collaborator_id):
                    flash('Selected collaborator does not exist.', 'danger')
                    return redirect(url_for('find_collaborators'))
                
                # Validate the project exists and belongs to the sender
                if not validate_project_exists(cursor, project_id, current_user.id):
                    flash('Invalid project selected.', 'danger')
                    return redirect(url_for('find_collaborators'))
                
                # Check for existing pending request
                if check_existing_request(cursor, current_user.id, collaborator_id, project_id):
                    flash('A pending collaboration request already exists for this project and collaborator.', 'warning')
                    return redirect(url_for('find_collaborators'))
                
                # Insert the collaboration request
                cursor.execute("""
                    INSERT INTO collaboration_request 
                    (sender_id, receiver_id, project_id, status) 
                    VALUES (%s, %s, %s, 'pending')
                """, (str(current_user.id), str(collaborator_id), str(project_id)))
                
                conn.commit()
                flash('Collaboration request sent successfully.', 'success')
                
            except Error as e:
                conn.rollback()
                flash(f"Database error in find_collaborators: {str(e)}")
                flash('An error occurred while processing your request. Please try again.', 'danger')
                
            except Exception as e:
                conn.rollback()
                flash(f"Unexpected error in find_collaborators: {str(e)}")
                flash('An unexpected error occurred. Please try again.', 'danger')
                
            finally:
                cursor.close()
                conn.close()
                
        # GET request handling
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get all researchers except current user
            cursor.execute("""
                SELECT researcher_id, email, f_name, l_name 
                FROM researcher 
                WHERE researcher_id <> %s
            """, (str(current_user.id),))
            collaborators = cursor.fetchall()
            
            # Get projects created by current user
            cursor.execute("""
                SELECT project_id, name 
                FROM project 
                WHERE creator_id = %s
            """, (str(current_user.id),))
            projects = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return render_template('find_collaborators.html', 
                                collaborators=collaborators, 
                                projects=projects)
            
        except Error as e:
            flash(f"Database error while fetching data: {str(e)}")
            flash('Error loading collaborator data. Please try again.', 'danger')
        return redirect(url_for('home'))
    
    @app.route('/my_collaborations')
    @login_required
    def my_collaborations():
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT c.collaboration_id, c.role, c.join_date, c.status, p.name AS project_name "
                        "FROM collaboration c "
                        "JOIN project p ON c.project_id = p.project_id "
                        "WHERE c.researcher_id = %s", (current_user.id,))
            collaborations = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('my_collaborations.html', collaborations=collaborations)
        except Error as e:
            flash(f'Error fetching collaborations: {e}', 'danger')
            return redirect(url_for('home'))
        
        
    @app.route('/collaboration_requests')
    @login_required
    def collaboration_requests():
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT cr.collaboration_request_id, cr.sender_id, r.f_name, r.l_name, cr.status, p.name AS project_name "
                        "FROM collaboration_request cr "
                        "JOIN researcher r ON cr.sender_id = r.researcher_id "
                        "JOIN project p ON cr.project_id = p.project_id "
                        "WHERE cr.receiver_id = %s", (current_user.id,))
            requests = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('collaboration_requests.html', requests=requests)
        except Error as e:
            flash(f'Error fetching collaboration requests: {e}', 'danger')
            return redirect(url_for('home'))

    @app.route('/accept_collaboration/<int:request_id>', methods=['POST'])
    @login_required
    def accept_collaboration(request_id):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE collaboration_request SET status = 'accepted' WHERE collaboration_request_id = %s", (request_id,))
            cursor.execute("INSERT INTO collaboration (collaboration_id, researcher_id, project_id, role, join_date, status) "
                        "SELECT %s, cr.sender_id, cr.project_id, 'Collaborator', NOW(), 'accepted' "
                        "FROM collaboration_request cr "
                        "WHERE cr.collaboration_request_id = %s", (str(uuid.uuid4()), request_id))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Collaboration request accepted successfully.', 'success')
        except Error as e:
            flash(f'Error accepting collaboration request: {e}', 'danger')
        return redirect(url_for('collaboration_requests'))

    @app.route('/decline_collaboration/<int:request_id>', methods=['POST'])
    @login_required
    def decline_collaboration(request_id):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE collaboration_request SET status = 'declined' WHERE collaboration_request_id = %s", (request_id,))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Collaboration request declined successfully.', 'success')
        except Error as e:
            flash(f'Error declining collaboration request: {e}', 'danger')
        return redirect(url_for('collaboration_requests'))


    @app.route('/write_review', methods=['GET', 'POST'])
    @login_required
    def write_review():
        if request.method == 'POST':
            paper_id = request.form.get('paper_id')
            comments = request.form.get('comments')

            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                reviewer_id = str(uuid.uuid4())
                insert_query = "INSERT INTO reviewer (reviewer_id, f_name, l_name, comments, paper_id) VALUES (%s, %s, %s, %s, %s)"
                values = (reviewer_id, current_user.id, current_user.email, comments, paper_id)
                cursor.execute(insert_query, values)
                conn.commit()
                flash('Review submitted successfully!', 'success')
                return redirect(url_for('write_review'))
            except Error as e:
                flash(f'Error submitting review: {str(e)}', 'danger')
                return render_template('write_review.html', paper_id=paper_id)
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()

        # Fetch the list of papers not written by the current user
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT paperid, title FROM research_paper WHERE researcher_id != %s", (current_user.id,))
            papers = cursor.fetchall()
            return render_template('write_review.html', papers=papers)
        except Error as e:
            flash(f'Error fetching papers: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    @app.route('/my_reviews')
    @login_required
    def my_reviews():
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # Fetch reviews written by the current user
            cursor.execute("""
                SELECT r.comments, p.title 
                FROM reviewer r
                JOIN research_paper p ON r.paper_id = p.paperid 
                WHERE r.f_name = %s AND r.l_name = %s
            """, (current_user.id, current_user.email))
            my_reviews = cursor.fetchall()

            # Fetch reviews received for the user's papers
            cursor.execute("""
                SELECT r.comments, r.f_name, r.l_name, p.title 
                FROM reviewer r
                JOIN research_paper p ON r.paper_id = p.paperid 
                WHERE p.researcher_id = %s
            """, (current_user.id,))
            received_reviews = cursor.fetchall()

            return render_template('my_reviews.html', my_reviews=my_reviews, received_reviews=received_reviews)
        except Error as e:
            flash(f'Error fetching reviews: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()


    @app.route('/papers_to_review')
    @login_required
    def papers_to_review():
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Fetch papers by other researchers that the current user hasn't reviewed
            cursor.execute("""
                SELECT p.paperid, p.title 
                FROM research_paper p 
                WHERE p.researcher_id != %s 
                AND p.paperid NOT IN (
                    SELECT paper_id FROM reviewer WHERE f_name = %s AND l_name = %s
                )
            """, (current_user.id, current_user.id, current_user.email))
            papers = cursor.fetchall()

            return render_template('papers_to_review.html', papers=papers)
        except Error as e:
            flash(f'Error fetching papers: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    
    
    @app.route('/add_funding_source', methods=['GET', 'POST'])
    @login_required
    def add_funding_source():
        if request.method == 'POST':
            print("Handling POST request for add_funding_source")
            name = request.form.get('name', '').strip()
            organization = request.form.get('organization', '').strip()

            if not name or not organization:
                print("Name or organization is missing")
                flash('Both name and organization are required.', 'danger')
                return render_template('add_funding_source.html')

            try:
                print("Attempting to connect to database")
                conn = get_db_connection()
                if not conn:
                    print("Database connection failed")
                    flash('Database connection failed', 'danger')
                    return render_template('add_funding_source.html')

                cursor = conn.cursor()
                print("Executing SQL query to insert funding source")
                cursor.execute("SELECT generate_funding_source_id()")
                funding_source_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO funding_source (funding_source_id, name, organization) VALUES (%s, %s, %s)", (funding_source_id, name, organization))
                conn.commit()
                print("Funding source added successfully")

                flash('Funding source added successfully.', 'success')
                return redirect(url_for('view_funding_sources'))

            except Error as e:
                print(f"Error adding funding source: {str(e)}")
                flash(f'Failed to add funding source: {str(e)}', 'danger')
                return render_template('add_funding_source.html')

            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()
        

        return render_template('add_funding_source.html')
    @app.route('/edit_funding_source/<funding_source_id>', methods=['GET', 'POST'])
    @login_required
    def edit_funding_source(funding_source_id):
        if request.method == 'GET':
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM funding_source WHERE funding_source_id = %s", (funding_source_id,))
                funding_source = cursor.fetchone()
                
                if not funding_source:
                    flash('Funding source not found', 'danger')
                    return redirect(url_for('view_funding_sources'))
                    
                return render_template('edit_funding_source.html', funding_source=funding_source)
                
            except Error as e:
                flash(f'Error retrieving funding source: {str(e)}', 'danger')
                return redirect(url_for('view_funding_sources'))
                
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()
                    
        elif request.method == 'POST':
            name = request.form.get('name', '').strip()
            organization = request.form.get('organization', '').strip()
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                update_query = """
                    UPDATE funding_source 
                    SET name = %s, organization = %s
                    WHERE funding_source_id = %s
                """
                cursor.execute(update_query, (name, organization, funding_source_id))
                conn.commit()
                
                flash('Funding source updated successfully', 'success')
                return redirect(url_for('view_funding_sources'))
                
            except Error as e:
                flash(f'Failed to update funding source: {str(e)}', 'danger')
                return redirect(url_for('edit_funding_source', funding_source_id=funding_source_id))
                
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()

    
    @app.route('/view_funding_sources')
    @login_required
    def view_funding_sources():
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'danger')
                return redirect(url_for('dashboard'))

            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM funding_source ORDER BY name")
            funding_sources = cursor.fetchall()

            return render_template('view_funding_sources.html', funding_sources=funding_sources)

        except Error as e:
            flash(f'Failed to retrieve funding sources: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    return app
