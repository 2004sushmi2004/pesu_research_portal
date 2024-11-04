SECRET_KEY = 'your-secret-key'
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'Unlock%402004'
MYSQL_DB = 'pesu_research_portal'

# If you're using a Config class, define it here
class Config:
    SECRET_KEY = SECRET_KEY
    MYSQL_HOST = MYSQL_HOST
    MYSQL_USER = MYSQL_USER
    MYSQL_PASSWORD = MYSQL_PASSWORD
    MYSQL_DB = MYSQL_DB
    SQLALCHEMY_DATABASE_URI = f"mysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:3306/{MYSQL_DB}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False