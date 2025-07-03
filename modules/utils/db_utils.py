import pymysql

class MariaDBManager:
    def __init__(self, host, user, password, port=3306):
        self.host = host
        self.user = user
        self.password = password
        self.port = int(port)

    def test_connection(self, database=None):
        try:
            conn = pymysql.connect(host=self.host, user=self.user, password=self.password, database=database, port=self.port, connect_timeout=3)
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

    def create_user_and_db(self, db_name, db_user, db_pass):
        try:
            conn = pymysql.connect(host=self.host, user=self.user, password=self.password, port=self.port)
            with conn.cursor() as cur:
                cur.execute(f"CREATE USER IF NOT EXISTS '{db_user}'@'127.0.0.1' IDENTIFIED BY '{db_pass}';")
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`;")
                cur.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'127.0.0.1' WITH GRANT OPTION;")
                cur.execute("FLUSH PRIVILEGES;")
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

    def drop_db_and_user(self, db_name, db_user):
        try:
            conn = pymysql.connect(host=self.host, user=self.user, password=self.password, port=self.port)
            with conn.cursor() as cur:
                cur.execute(f"DROP DATABASE IF EXISTS `{db_name}`;")
                cur.execute(f"DROP USER IF EXISTS '{db_user}'@'127.0.0.1';")
                cur.execute("FLUSH PRIVILEGES;")
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

    def reset_password(self, db_user, new_pass):
        try:
            conn = pymysql.connect(host=self.host, user=self.user, password=self.password, port=self.port)
            with conn.cursor() as cur:
                cur.execute(f"ALTER USER '{db_user}'@'127.0.0.1' IDENTIFIED BY '{new_pass}';")
                cur.execute("FLUSH PRIVILEGES;")
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e) 