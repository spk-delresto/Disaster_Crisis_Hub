import pymysql
import config


def get_connection():
    try:
        conn = pymysql.connect(
            host=config.MYSQL_HOST,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DATABASE,
            cursorclass=pymysql.cursors.DictCursor,
        )

        print("Database connected successfully!")
        return conn

    except Exception as e:
        print("Database connection failed:")
        print(e)

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create default admin if not exists
    cursor.execute("SELECT * FROM users WHERE email = %s", ("admin@admin.com",))
    if not cursor.fetchone():
        from werkzeug.security import generate_password_hash

        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
            ("Admin", "admin@admin.com", generate_password_hash("admin123"), "admin"),
        )

    conn.commit()
    cursor.close()
    conn.close()
