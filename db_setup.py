import mariadb

def setup_database():
    try:
        connection = mariadb.connect(
            host="localhost",
            user="root",
            password=""
        )
        cursor = connection.cursor()

        # Create the database
        cursor.execute("CREATE DATABASE IF NOT EXISTS smart_door_lock")
        cursor.execute("USE smart_door_lock")

        # Create tables
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS TemporaryQR (
            id INT AUTO_INCREMENT PRIMARY KEY,
            key_id VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("Database and tables created successfully!")
    except mariadb.Error as err:
        print(f"Error: {err}")
    finally:
        if connection:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    setup_database()