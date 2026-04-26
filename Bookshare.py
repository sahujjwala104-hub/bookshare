import mysql.connector
from datetime import date
from tabulate import tabulate
import getpass

# ---------- DATABASE CONNECTION ----------
con = mysql.connector.connect(
    user="root",
    password="ujjwala0406",
    host="localhost",
    database="bookshare"
)

if con.is_connected():
    print(" Connected to MySQL Database")
else:
    print(" Connection Failed")

mycursor = con.cursor()

# Global variable to store logged-in user
current_user = None


# ---------- TABLE CREATION ----------
def create_tables():
    mycursor.execute("""
    CREATE TABLE IF NOT EXISTS User(
        User_id INT AUTO_INCREMENT PRIMARY KEY,
        Name VARCHAR(100) NOT NULL,
        Email VARCHAR(100) UNIQUE NOT NULL,
        Password VARCHAR(100),
        Phone VARCHAR(15),
        City VARCHAR(100),
        Address VARCHAR(255),
        Is_Admin BOOLEAN DEFAULT FALSE
    );""")

    mycursor.execute("""
    CREATE TABLE IF NOT EXISTS Category(
        Category_id INT AUTO_INCREMENT PRIMARY KEY,
        Category_Name VARCHAR(100) NOT NULL
    );""")

    mycursor.execute("""
    CREATE TABLE IF NOT EXISTS Genre(
        Genre_id INT AUTO_INCREMENT PRIMARY KEY,
        Genre_Name VARCHAR(100) NOT NULL,
        Category_id INT,
        FOREIGN KEY (Category_id) REFERENCES Category(Category_id)
    );""")

    mycursor.execute("""
    CREATE TABLE IF NOT EXISTS Book(
        Book_id INT AUTO_INCREMENT PRIMARY KEY,
        Title VARCHAR(200) NOT NULL,
        Author VARCHAR(100),
        ISBN VARCHAR(30),
        Publisher VARCHAR(100),
        Genre_id INT,
        Category_id INT,
        FOREIGN KEY (Genre_id) REFERENCES Genre(Genre_id),
        FOREIGN KEY (Category_id) REFERENCES Category(Category_id)
    );""")

    mycursor.execute("""
    CREATE TABLE IF NOT EXISTS BookOwner(
        Owner_id INT,
        Book_id INT,
        Activity_type ENUM('sell','lend','donate'),
        Available BOOLEAN DEFAULT TRUE,
        Price DECIMAL(10,2),
        PRIMARY KEY (Owner_id, Book_id),
        FOREIGN KEY (Owner_id) REFERENCES User(User_id),
        FOREIGN KEY (Book_id) REFERENCES Book(Book_id)
    );""")

    mycursor.execute("""
    CREATE TABLE IF NOT EXISTS BookActivity(
        Activity_id INT AUTO_INCREMENT PRIMARY KEY,
        Owner_id INT,
        Receiver_id INT,
        Book_id INT,
        Activity_type ENUM('buy','borrow','donation') NOT NULL,
        Date DATE,
        Price DECIMAL(10,2),
        Return_Date DATE,
        FOREIGN KEY (Owner_id) REFERENCES User(User_id),
        FOREIGN KEY (Receiver_id) REFERENCES User(User_id),
        FOREIGN KEY (Book_id) REFERENCES Book(Book_id)
    );""")

    mycursor.execute("""
    CREATE TABLE IF NOT EXISTS Review(
        Review_id INT AUTO_INCREMENT PRIMARY KEY,
        Book_id INT,
        User_id INT,
        Rating INT CHECK(Rating BETWEEN 1 AND 5),
        Comment TEXT,
        Date DATE,
        FOREIGN KEY (Book_id) REFERENCES Book(Book_id),
        FOREIGN KEY (User_id) REFERENCES User(User_id)
    );""")

    con.commit()
    print("Tables created successfully!")


# ---------- AUTHENTICATION ----------
def register_user():
    print("\n--- User Registration ---")
    name = input("Enter Name: ")
    email = input("Enter Email: ")
    password = getpass.getpass("Enter Password: ")
    confirm_password = getpass.getpass("Confirm Password: ")
    
    if password != confirm_password:
        print("Passwords don't match!")
        return
    
    phone = input("Enter Phone: ")
    city = input("Enter City: ")
    address = input("Enter Address: ")
    
    try:
        mycursor.execute("""
            INSERT INTO User (Name, Email, Password, Phone, City, Address, Is_Admin)
            VALUES (%s,%s,%s,%s,%s,%s,FALSE)
        """, (name, email, password, phone, city, address))
        con.commit()
        print("Registration successful! You can now login.")
    except mysql.connector.IntegrityError:
        print("Email already exists!")


def login():
    global current_user
    print("\n--- Login ---")
    email = input("Enter Email: ")
    password = getpass.getpass("Enter Password: ")
    
    mycursor.execute("""
        SELECT User_id, Name, Email, Is_Admin 
        FROM User 
        WHERE Email = %s AND Password = %s
    """, (email, password))
    
    result = mycursor.fetchone()
    
    if result:
        current_user = {
            'id': result[0],
            'name': result[1],
            'email': result[2],
            'is_admin': result[3]
        }
        print(f"\n Welcome, {current_user['name']}!")
        return True
    else:
        print("Invalid credentials!")
        return False


# ---------- ADMIN FUNCTIONS ----------
def add_category():
    name = input("Enter Category Name: ")
    mycursor.execute("INSERT INTO Category (Category_Name) VALUES (%s)", (name,))
    con.commit()
    print("📚 Category added!")


def add_genre():
    # Show available categories
    mycursor.execute("SELECT Category_id, Category_Name FROM Category")
    categories = mycursor.fetchall()
    print("\nAvailable Categories:")
    print(tabulate(categories, headers=["ID", "Category"], tablefmt="simple"))
    
    name = input("\nEnter Genre Name: ")
    category_id = int(input("Enter Category ID: "))
    mycursor.execute("INSERT INTO Genre (Genre_Name, Category_id) VALUES (%s,%s)", (name, category_id))
    con.commit()
    print("🎭 Genre added!")


def view_all_users():
    mycursor.execute("SELECT User_id, Name, Email, Phone, City FROM User WHERE Is_Admin = FALSE")
    result = mycursor.fetchall()
    print(tabulate(result, headers=["ID", "Name", "Email", "Phone", "City"], tablefmt="grid"))


def view_all_books():
    mycursor.execute("""
        SELECT Book.Book_id, Title, Author, Genre_Name, Category_Name, Publisher
        FROM Book
        LEFT JOIN Genre ON Book.Genre_id = Genre.Genre_id
        LEFT JOIN Category ON Book.Category_id = Category.Category_id
    """)
    result = mycursor.fetchall()
    print(tabulate(result, headers=["ID", "Title", "Author", "Genre", "Category", "Publisher"], tablefmt="grid"))


def view_book_activities():
    mycursor.execute("""
        SELECT a.Activity_id, b.Title, u1.Name AS Owner, u2.Name AS Receiver, 
               a.Activity_type, a.Date, a.Price
        FROM BookActivity a
        JOIN Book b ON a.Book_id = b.Book_id
        JOIN User u1 ON a.Owner_id = u1.User_id
        JOIN User u2 ON a.Receiver_id = u2.User_id
        ORDER BY a.Date DESC
    """)
    result = mycursor.fetchall()
    print(tabulate(result, headers=["Activity ID","Book","Owner","Receiver","Type","Date","Price"], tablefmt="grid"))


# ---------- USER FUNCTIONS ----------
def add_my_book():
    print("\n--- Add Your Book ---")
    
    # Show categories and genres
    mycursor.execute("SELECT Category_id, Category_Name FROM Category")
    categories = mycursor.fetchall()
    print("\nAvailable Categories:")
    print(tabulate(categories, headers=["ID", "Category"], tablefmt="simple"))
    
    category_id = int(input("\nSelect Category ID: "))
    
    mycursor.execute("SELECT Genre_id, Genre_Name FROM Genre WHERE Category_id = %s", (category_id,))
    genres = mycursor.fetchall()
    print("\nAvailable Genres:")
    print(tabulate(genres, headers=["ID", "Genre"], tablefmt="simple"))
    
    title = input("\nEnter Book Title: ")
    author = input("Enter Author: ")
    isbn = input("Enter ISBN (optional): ")
    publisher = input("Enter Publisher (optional): ")
    genre_id = int(input("Select Genre ID: "))
    
    # Check if book already exists
    mycursor.execute("SELECT Book_id FROM Book WHERE ISBN = %s AND ISBN != ''", (isbn,))
    existing = mycursor.fetchone()
    
    if existing and isbn:
        book_id = existing[0]
        print(f"📖 Book already exists in database (ID: {book_id})")
    else:
        mycursor.execute("""
            INSERT INTO Book (Title, Author, ISBN, Publisher, Genre_id, Category_id)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (title, author, isbn, publisher, genre_id, category_id))
        con.commit()
        book_id = mycursor.lastrowid
        print(f"📖 New book added (ID: {book_id})")
    
    # Add ownership
    activity_type = input("What do you want to do? (sell/lend/donate): ").lower()
    price = 0
    if activity_type in ['sell', 'lend']:
        price = float(input("Enter price: "))
    
    mycursor.execute("""
        INSERT INTO BookOwner (Owner_id, Book_id, Activity_type, Available, Price)
        VALUES (%s,%s,%s,TRUE,%s)
    """, (current_user['id'], book_id, activity_type, price))
    con.commit()
    print("Your book has been listed!")


def browse_available_books():
    print("\n--- Available Books ---")
    mycursor.execute("""
        SELECT b.Book_id, b.Title, b.Author, bo.Activity_type, bo.Price, 
               u.Name AS Owner, u.City
        FROM Book b
        JOIN BookOwner bo ON b.Book_id = bo.Book_id
        JOIN User u ON bo.Owner_id = u.User_id
        WHERE bo.Available = TRUE AND bo.Owner_id != %s
    """, (current_user['id'],))
    result = mycursor.fetchall()
    
    if result:
        print(tabulate(result, headers=["ID", "Title", "Author", "Type", "Price", "Owner", "City"], tablefmt="grid"))
    else:
        print("No books available at the moment.")

def search_books():
    keyword = input("Enter keyword to search (Title/Author/Genre): ")
    mycursor.execute("""
        SELECT b.Book_id, b.Title, b.Author, g.Genre_Name, c.Category_Name,
               COALESCE(bo.Activity_type, 'N/A') AS Activity_type, 
               COALESCE(bo.Price, 0) AS Price, 
               CASE 
                   WHEN bo.Owner_id = %s THEN 'You'
                   ELSE COALESCE(u.Name, 'N/A')
               END AS Owner,
               COALESCE(u.City, 'N/A') AS City
        FROM Book b
        LEFT JOIN Genre g ON b.Genre_id = g.Genre_id
        LEFT JOIN Category c ON b.Category_id = c.Category_id
        LEFT JOIN BookOwner bo ON b.Book_id = bo.Book_id
        LEFT JOIN User u ON bo.Owner_id = u.User_id
        WHERE (b.Title LIKE %s OR b.Author LIKE %s OR g.Genre_Name LIKE %s)
              AND (bo.Available = TRUE OR bo.Available IS NULL)
    """, (current_user['id'], f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
    result = mycursor.fetchall()
    
    if result:
        print(tabulate(result, headers=["ID", "Title", "Author", "Genre", "Category", "Type", "Price", "Owner", "City"], tablefmt="grid"))
    else:
        print("No books found matching your search.")


def request_book():
    book_id = int(input("Enter Book ID to request: "))
    
    # Get book and owner details
    mycursor.execute("""
        SELECT bo.Owner_id, bo.Activity_type, bo.Price, b.Title, u.Name, u.Phone
        FROM BookOwner bo
        JOIN Book b ON bo.Book_id = b.Book_id
        JOIN User u ON bo.Owner_id = u.User_id
        WHERE bo.Book_id = %s AND bo.Available = TRUE
    """, (book_id,))
    
    result = mycursor.fetchone()
    
    if not result:
        print("Book not available!")
        return
    
    owner_id, activity_type, price, title, owner_name, owner_phone = result
    
    if owner_id == current_user['id']:
        print("This is your own book!")
        return
    
    print(f"\n📖 Book: {title}")
    print(f"👤 Owner: {owner_name}")
    print(f"📞 Contact: {owner_phone}")
    print(f"💰 Price: ₹{price}")
    print(f"📝 Type: {activity_type}")
    
    confirm = input("\nConfirm request? (yes/no): ").lower()
    
    if confirm == 'yes':
        activity_map = {'sell': 'buy', 'lend': 'borrow', 'donate': 'donation'}
        receiver_activity = activity_map[activity_type]
        today = date.today()
        
        mycursor.execute("""
            INSERT INTO BookActivity (Owner_id, Receiver_id, Book_id, Activity_type, Date, Price)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (owner_id, current_user['id'], book_id, receiver_activity, today, price))
        
        # Mark as unavailable if sold or donated
        if activity_type in ['sell', 'donate']:
            mycursor.execute("""
                UPDATE BookOwner SET Available = FALSE 
                WHERE Owner_id = %s AND Book_id = %s
            """, (owner_id, book_id))
        
        con.commit()
        print("Request recorded! Contact the owner to complete the transaction.")
    else:
        print("Request cancelled.")


def view_my_books():
    print("\n--- My Listed Books ---")
    mycursor.execute("""
        SELECT b.Book_id, b.Title, b.Author, bo.Activity_type, bo.Price, bo.Available
        FROM Book b
        JOIN BookOwner bo ON b.Book_id = bo.Book_id
        WHERE bo.Owner_id = %s
    """, (current_user['id'],))
    result = mycursor.fetchall()
    
    if result:
        print(tabulate(result, headers=["ID", "Title", "Author", "Type", "Price", "Available"], tablefmt="grid"))
    else:
        print("You haven't listed any books yet.")


def view_my_activities():
    print("\n--- My Book Activities ---")
    mycursor.execute("""
        SELECT ba.Activity_id, b.Title, 
               CASE 
                   WHEN ba.Owner_id = %s THEN u2.Name
                   ELSE u1.Name
               END AS Other_Party,
               ba.Activity_type,
               CASE 
                   WHEN ba.Owner_id = %s THEN 'Provided'
                   ELSE 'Received'
               END AS Direction,
               ba.Date, ba.Price
        FROM BookActivity ba
        JOIN Book b ON ba.Book_id = b.Book_id
        JOIN User u1 ON ba.Owner_id = u1.User_id
        JOIN User u2 ON ba.Receiver_id = u2.User_id
        WHERE ba.Owner_id = %s OR ba.Receiver_id = %s
        ORDER BY ba.Date DESC
    """, (current_user['id'], current_user['id'], current_user['id'], current_user['id']))
    result = mycursor.fetchall()
    
    if result:
        print(tabulate(result, headers=["ID", "Book", "Other Party", "Type", "Direction", "Date", "Price"], tablefmt="grid"))
    else:
        print("No activities yet.")


def add_review():
    book_name = input("Enter Book Title to review: ")
    
    # Resolve book name to ID
    mycursor.execute("SELECT Book_id, Title FROM Book WHERE Title LIKE %s", (f"%{book_name}%",))
    books = mycursor.fetchall()
    
    if not books:
        print("No book found with that name!")
        return
    
    if len(books) > 1:
        print("\nMultiple books found:")
        print(tabulate(books, headers=["ID", "Title"], tablefmt="simple"))
        book_id = int(input("Enter the Book ID from above: "))
    else:
        book_id = books[0][0]
        print(f"Found: {books[0][1]}")
    
    # Check if user has received this book
    mycursor.execute("""
        SELECT b.Title FROM Book b
        JOIN BookActivity ba ON b.Book_id = ba.Book_id
        WHERE b.Book_id = %s AND ba.Receiver_id = %s
    """, (book_id, current_user['id']))
    
    if not mycursor.fetchone():
        print("You can only review books you've received!")
        return
    
    rating = int(input("Enter Rating (1-5): "))
    if not 1 <= rating <= 5:
        print("Rating must be between 1 and 5!")
        return
    comment = input("Enter Comment: ")
    
    mycursor.execute("""
        INSERT INTO Review (Book_id, User_id, Rating, Comment, Date)
        VALUES (%s,%s,%s,%s,%s)
    """, (book_id, current_user['id'], rating, comment, date.today()))
    con.commit()
    print("⭐ Review added!")


def view_reviews():
    book_name = input("Enter Book Title to view reviews: ")
    
    # Resolve book name to ID
    mycursor.execute("SELECT Book_id, Title FROM Book WHERE Title LIKE %s", (f"%{book_name}%",))
    books = mycursor.fetchall()
    
    if not books:
        print("No book found with that name!")
        return
    
    if len(books) > 1:
        print("\nMultiple books found:")
        print(tabulate(books, headers=["ID", "Title"], tablefmt="simple"))
        book_id = int(input("Enter the Book ID from above: "))
        title = next(b[1] for b in books if b[0] == book_id)
    else:
        book_id = books[0][0]
        title = books[0][1]
    
    mycursor.execute("""
        SELECT u.Name, r.Rating, r.Comment, r.Date
        FROM Review r
        JOIN User u ON r.User_id = u.User_id
        WHERE r.Book_id = %s
        ORDER BY r.Date DESC
    """, (book_id,))
    result = mycursor.fetchall()
    
    if result:
        print(f"\n--- Reviews for '{title}' ---")
        print(tabulate(result, headers=["Reviewer", "Rating", "Comment", "Date"], tablefmt="fancy_grid"))
    else:
        print(f"No reviews yet for '{title}'.")


# ---------- ADMIN MENU ----------
def admin_menu():
    while True:
        print(f"\n====== ADMIN PANEL - Welcome {current_user['name']} ======")
        print("1. Add Category")
        print("2. Add Genre")
        print("3. View All Users")
        print("4. View All Books")
        print("5. View All Activities")
        print("0. Logout")
        
        choice = input("\nEnter your choice: ")
        
        if choice == "1":
            add_category()
        elif choice == "2":
            add_genre()
        elif choice == "3":
            view_all_users()
        elif choice == "4":
            view_all_books()
        elif choice == "5":
            view_book_activities()
        elif choice == "0":
            return
        else:
            print("Invalid choice!")


# ---------- USER MENU ----------
def user_menu():
    while True:
        print(f"\n====== BookShare - Welcome {current_user['name']} ======")
        print("1. Add My Book")
        print("2. Browse Available Books")
        print("3. Search Books")
        print("4. Request a Book")
        print("5. View My Books")
        print("6. View My Activities")
        print("7. Write a Review")
        print("8. View Book Reviews")
        print("0. Logout")
        
        choice = input("\nEnter your choice: ")
        
        if choice == "1":
            add_my_book()
        elif choice == "2":
            browse_available_books()
        elif choice == "3":
            search_books()
        elif choice == "4":
            request_book()
        elif choice == "5":
            view_my_books()
        elif choice == "6":
            view_my_activities()
        elif choice == "7":
            add_review()
        elif choice == "8":
            view_reviews()
        elif choice == "0":
            return
        else:
            print("Invalid choice!")


# ---------- MAIN FUNCTION ----------
def main():
    global current_user
    create_tables()
    
    # Create default admin if doesn't exist
    mycursor.execute("SELECT * FROM User WHERE Is_Admin = TRUE")
    if not mycursor.fetchone():
        mycursor.execute("""
            INSERT INTO User (Name, Email, Password, Phone, City, Address, Is_Admin)
            VALUES ('Admin','admin@bookshare.com','admin123','0000000000','System','System',TRUE)
        """)
        con.commit()
    
    while True:
        print("\n╔══════════════════════════════════════╗")
        print("║    📚 BookShare Platform 📚          ║")
        print("╚══════════════════════════════════════╝")
        print("1. Login")
        print("2. Register")
        print("0. Exit")
        
        choice = input("\nEnter your choice: ")
        
        if choice == "1":
            if login():
                if current_user['is_admin']:
                    admin_menu()
                else:
                    user_menu()
                current_user = None
        elif choice == "2":
            register_user()
        elif choice == "0":
            print("👋 Thank you for using BookShare!")
            break
        else:
            print("Invalid choice!")
    
    con.close()


if __name__ == "__main__":
    main()
