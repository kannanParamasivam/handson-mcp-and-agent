import sqlite3


class TimeOffDatastore:


    def __init__(self, db_path=":memory:"):
        # Initialize the database connection
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
        self.seed_data()
        

    def create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employee (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                allowed_days INTEGER NOT NULL,
                consumed_days INTEGER NOT NULL DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS timeoff_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                start_day TEXT NOT NULL,
                total_days INTEGER NOT NULL,
                FOREIGN KEY(employee_id) REFERENCES employee(id)
            )
        ''')
        
        self.conn.commit()


    def seed_data(self):
        cursor = self.conn.cursor()
        employees = [
            ("Alice", 20, 5),
            ("Bob", 15, 3),
            ("Charlie", 25, 10)
        ]

        for name, allowed, consumed in employees:
            cursor.execute('''
                INSERT OR IGNORE INTO employee (name, allowed_days, consumed_days)
                VALUES (?, ?, ?)
            ''', (name, allowed, consumed))

        self.conn.commit()


    def get_timeoff_balance(self, employee_name):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT allowed_days, consumed_days FROM employee WHERE name = ?
        ''', (employee_name,))
        row = cursor.fetchone()
        
        if row:
            allowed, consumed = row
            return allowed - consumed
        else:
            return None


    def add_timeoff_request(self, employee_name, start_day, total_days):
        cursor = self.conn.cursor()

        # Find employee and current timeoff balance
        cursor.execute('SELECT id, allowed_days, consumed_days FROM employee WHERE name = ?', (employee_name,))
        row = cursor.fetchone()        
        if not row:
            raise ValueError(f"Employee {employee_name} not found")
        employee_id, allowed_days, consumed_days = row # unpack employee data
        if consumed_days + total_days > allowed_days:
            raise ValueError(f"Employee {employee_name} does not have enough time off balance to request {total_days} days (current balance: {allowed_days - consumed_days} days)")
        
        # insert into timeoff history
        cursor.execute('''
            INSERT INTO timeoff_history (employee_id, start_day, total_days)
            VALUES (?, ?, ?)
        ''', (employee_id, start_day, total_days))

        # update time off balance
        new_consumed = consumed_days + total_days
        cursor.execute('''
            UPDATE employee SET consumed_days = ? WHERE id = ?
        ''', (new_consumed, employee_id))

        self.conn.commit()
        return f"Successfully added timeoff request for {total_days} days for employee {employee_name}"


if __name__ == "__main__":
    db = TimeOffDatastore()
    # db.seed_data()  # Removed since seed_data() is already called in __init__
    
    # Test getting balance
    balance = db.get_timeoff_balance("Alice")
    print(f"Alice's balance: {balance} days")
    
    # Test adding timeoff request
    try:
        db.add_timeoff_request("Alice", "2025-06-01", 2)
        new_balance = db.get_timeoff_balance("Alice")
        print(f"Alice's new balance after request: {new_balance} days")
    except ValueError as e:
        print(f"Error: {e}")

        

        
        




