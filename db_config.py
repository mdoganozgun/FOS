import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="happy34Moonlight",     # Buraya kendi şifreni yaz
        database="fos"  # Veritabanı adını yaz
    )