from flask import Flask, redirect, url_for, flash, render_template, request, send_file, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
import io
import uuid
from datetime import datetime
import os

class User:
    def __init__(self, id, email):
        self.id = id
        self.email = email
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
            cursor.execute("SELECT * FROM researcher WHERE researcher_id = %s", (user_id,))
            user_data = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user_data:
                return User(user_data['researcher_id'], user_data['email'])
            return None
        except Error as e:
            print(f"Error loading user: {e}")
            return None
        
    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
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
                return render_template('register.html')

            try:
                conn = get_db_connection()
                if not conn:
                    flash('Database connection failed', 'danger')
                    return render_template('register.html')

                cursor = conn.cursor()
                
                # Check if email already exists
                cursor.execute("SELECT email FROM researcher WHERE email = %s", (email,))
                if cursor.fetchone():
                    flash('Email already registered', 'danger')
                    return render_template('register.html')

                # Generate unique researcher_id and hash password
                researcher_id = str(uuid.uuid4())
                hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
                
                # Insert new researcher
                insert_query = """
                    INSERT INTO researcher 
                    (researcher_id, email, password, f_name, l_name, expertise, affiliation)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                values = (
                    researcher_id,
                    email,
                    hashed_password,
                    f_name,
                    l_name,
                    expertise,
                    affiliation
                )
                
                cursor.execute(insert_query, values)
                conn.commit()
                
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))

            except Error as e:
                flash(f'Registration failed: {str(e)}', 'danger')
                return render_template('register.html')
                
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()
        
        return render_template('register.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
            
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            
            if not email or not password:
                flash('Please enter both email and password', 'danger')
                return render_template('login.html')
                
            try:
                conn = get_db_connection()
                if not conn:
                    flash('Database connection failed', 'danger')
                    return render_template('login.html')
                    
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM researcher WHERE email = %s", (email,))
                user_data = cursor.fetchone()
                
                if user_data and check_password_hash(user_data['password'], password):
                    user = User(user_data['researcher_id'], user_data['email'])
                    login_user(user)
                    return redirect(url_for('dashboard'))
                else:
                    flash('Invalid email or password', 'danger')
                    
            except Error as e:
                flash(f'Login failed: {str(e)}', 'danger')
                
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()
                    
        return render_template('login.html')

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

            # Generate unique paperid
            paperid = str(uuid.uuid4())

            try:
                conn = get_db_connection()
                if not conn:
                    flash('Database connection failed', 'danger')
                    return render_template('upload_paper.html')

                cursor = conn.cursor()

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
                return redirect(url_for('dashboard'))

            except Error as e:
                flash(f'Failed to upload paper: {str(e)}', 'danger')
                return render_template('upload_paper.html')

            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()

        return render_template('upload_paper.html')
    
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
                file_data = paper_data[0]
                file_name = f"{paper_data[1]}.pdf"
                return send_file(io.BytesIO(file_data), mimetype='application/pdf', as_attachment=True, download_name=file_name)
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
            flash(f'Failed to delete paper: {str(e)}', 'danger')
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
                return redirect(url_for('dashboard'))

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


    return app
