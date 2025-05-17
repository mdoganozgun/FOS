import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="efeS2003",     # Buraya kendi şifreni yaz
        database="food_ordering_system"  # Veritabanı adını yaz
    )