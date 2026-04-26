from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from datetime import date
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)


def get_db():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME")
    )

# ---------------- Register ----------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    try:
        # Hash the password before storing it
        hashed_pw = generate_password_hash(data["password"])

        db = get_db()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO User (Name, Email, Password, Phone, City, Address, Is_Admin)
            VALUES (%s,%s,%s,%s,%s,%s,FALSE)
        """, (data["name"], data["email"], hashed_pw,
              data["phone"], data["city"], data["address"]))
        db.commit()
        cur.close(); db.close()
        return jsonify({"success": True, "message": "Registered successfully"})
    except mysql.connector.IntegrityError:
        return jsonify({"success": False, "message": "Email already exists"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------------- Login ----------------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        # Fetch the user by email only, then verify password separately
        cur.execute("""
            SELECT User_id, Name, Email, Phone, City, Address, Is_Admin, Password
            FROM User WHERE Email=%s
        """, (data["email"],))
        user = cur.fetchone()
        cur.close(); db.close()

        if user and check_password_hash(user["Password"], data["password"]):
            # Remove the password hash before sending back to frontend
            user.pop("Password")
            return jsonify({"success": True, "user": user})

        return jsonify({"success": False, "message": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------------- Categories ----------------
@app.route("/api/categories", methods=["GET"])
def categories():
    try:
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("SELECT Category_id, Category_Name FROM Category")
        data = cur.fetchall()
        cur.close(); db.close()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------------- Genres ----------------
@app.route("/api/genres", methods=["GET"])
def genres():
    try:
        category_id = request.args.get("category_id")
        db = get_db(); cur = db.cursor(dictionary=True)
        if category_id:
            cur.execute("SELECT Genre_id, Genre_Name FROM Genre WHERE Category_id=%s", (category_id,))
        else:
            cur.execute("SELECT Genre_id, Genre_Name FROM Genre")
        data = cur.fetchall()
        cur.close(); db.close()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------------- Add Book ----------------
@app.route("/api/books", methods=["POST"])
def add_book():
    data = request.json
    try:
        db = get_db(); cur = db.cursor()
        cur.execute("""
            INSERT INTO Book (Title, Author, ISBN, Publisher, Genre_id, Category_id)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (data["title"], data["author"], data.get("isbn", ""),
              data.get("publisher", ""), data["genre_id"], data["category_id"]))
        db.commit()
        book_id = cur.lastrowid
        cur.execute("""
            INSERT INTO BookOwner (Owner_id, Book_id, Activity_type, Available, Price)
            VALUES (%s,%s,%s,TRUE,%s)
        """, (data["user_id"], book_id, data["activity_type"], data.get("price", 0)))
        db.commit()
        cur.close(); db.close()
        return jsonify({"success": True, "message": "Book added successfully", "book_id": book_id})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------------- Browse Available Books ----------------
@app.route("/api/books/available", methods=["GET"])
def get_available_books():
    try:
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT b.Book_id, b.Title, b.Author, bo.Activity_type, bo.Price, 
                   u.User_id AS Owner_id, u.Name AS Owner, u.City
            FROM Book b
            JOIN BookOwner bo ON b.Book_id = bo.Book_id
            JOIN User u ON bo.Owner_id = u.User_id
            WHERE bo.Available = TRUE
        """)
        data = cur.fetchall()
        cur.close(); db.close()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------------- Search Books ----------------
@app.route("/api/books/search", methods=["GET"])
def search_books():
    try:
        keyword = request.args.get("keyword", "")
        user_id = request.args.get("user_id")
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT b.Book_id, b.Title, b.Author, g.Genre_Name, bo.Activity_type, bo.Price,
                   u.User_id AS Owner_id, u.Name AS Owner
            FROM Book b
            JOIN BookOwner bo ON b.Book_id = bo.Book_id
            JOIN User u ON bo.Owner_id = u.User_id
            LEFT JOIN Genre g ON b.Genre_id = g.Genre_id
            WHERE (b.Title LIKE %s OR b.Author LIKE %s OR g.Genre_Name LIKE %s)
              AND bo.Available = TRUE AND u.User_id != %s
        """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", user_id))
        data = cur.fetchall()
        cur.close(); db.close()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------------- My Books ----------------
@app.route("/api/books/my-books", methods=["GET"])
def my_books():
    try:
        user_id = request.args.get("user_id")
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT b.Title, b.Author, bo.Activity_type, bo.Price, bo.Available
            FROM Book b JOIN BookOwner bo ON b.Book_id = bo.Book_id
            WHERE bo.Owner_id = %s
        """, (user_id,))
        data = cur.fetchall()
        cur.close(); db.close()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------------- Buy / Borrow Book ----------------
@app.route("/api/activities/request", methods=["POST"])
def request_book():
    data = request.json
    try:
        db = get_db(); cur = db.cursor(dictionary=True)

        cur.execute("""
            SELECT Name, Phone FROM User WHERE User_id = %s
        """, (data["owner_id"],))
        seller = cur.fetchone()

        if not seller:
            cur.close(); db.close()
            return jsonify({"success": False, "message": "Seller not found"}), 404

        cur.execute("SELECT Title FROM Book WHERE Book_id = %s", (data["book_id"],))
        book = cur.fetchone()
        book_title = book["Title"] if book else "the book"

        cur.execute("""
            INSERT INTO BookActivity (Owner_id, Receiver_id, Book_id, Activity_type, Date, Price)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (data["owner_id"], data["receiver_id"], data["book_id"],
              data["activity_type"], date.today(), data.get("price", 0)))

        cur.execute("""
            UPDATE BookOwner SET Available = FALSE
            WHERE Book_id = %s AND Owner_id = %s
        """, (data["book_id"], data["owner_id"]))

        db.commit()
        cur.close(); db.close()

        return jsonify({
            "success": True,
            "message": (
                f"Request recorded for '{book_title}'. "
                f"Please contact the seller to arrange delivery. "
                f"Payment is cash on delivery — no pre-payment required."
            ),
            "seller": {
                "name": seller["Name"],
                "phone": seller["Phone"]
            },
            "payment_note": "Cash on delivery only. Do not pay in advance."
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------------- My Activities ----------------
@app.route("/api/activities/my-activities", methods=["GET"])
def my_activities():
    try:
        user_id = request.args.get("user_id")
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT b.Title,
                   CASE WHEN a.Owner_id = %s THEN u2.Name ELSE u1.Name END AS Other_Party,
                   a.Activity_type,
                   CASE WHEN a.Owner_id = %s THEN 'Sent' ELSE 'Received' END AS Direction,
                   a.Date, a.Price
            FROM BookActivity a
            JOIN Book b ON a.Book_id = b.Book_id
            JOIN User u1 ON a.Owner_id = u1.User_id
            JOIN User u2 ON a.Receiver_id = u2.User_id
            WHERE a.Owner_id = %s OR a.Receiver_id = %s
            ORDER BY a.Date DESC
        """, (user_id, user_id, user_id, user_id))
        data = cur.fetchall()
        cur.close(); db.close()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------------- Get Reviews for a Book (by Book ID) ----------------
@app.route("/api/reviews/<int:book_id>", methods=["GET"])
def get_reviews(book_id):
    try:
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("SELECT Title FROM Book WHERE Book_id = %s", (book_id,))
        book = cur.fetchone()
        if not book:
            cur.close(); db.close()
            return jsonify({"success": False, "message": "Book not found"}), 404

        cur.execute("""
            SELECT r.Rating, r.Comment, r.Date, u.Name AS Reviewer
            FROM Review r
            JOIN User u ON r.User_id = u.User_id
            WHERE r.Book_id = %s
            ORDER BY r.Date DESC
        """, (book_id,))
        reviews = cur.fetchall()
        cur.close(); db.close()
        return jsonify({
            "success": True,
            "book_title": book["Title"],
            "data": reviews
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------------- Get Reviews for a Book (by Book Name) ----------------
@app.route("/api/reviews/by-name", methods=["GET"])
def get_reviews_by_name():
    try:
        book_name = request.args.get("title", "").strip()
        if not book_name:
            return jsonify({"success": False, "message": "title param required"}), 400
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("SELECT Book_id, Title FROM Book WHERE Title LIKE %s", (f"%{book_name}%",))
        book = cur.fetchone()
        if not book:
            cur.close(); db.close()
            return jsonify({"success": False, "message": "Book not found"}), 404
        cur.execute("""
            SELECT r.Rating, r.Comment, r.Date, u.Name AS Reviewer
            FROM Review r
            JOIN User u ON r.User_id = u.User_id
            WHERE r.Book_id = %s
            ORDER BY r.Date DESC
        """, (book["Book_id"],))
        reviews = cur.fetchall()
        cur.close(); db.close()
        return jsonify({
            "success": True,
            "book_title": book["Title"],
            "data": reviews
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------------- Submit a Review ----------------
@app.route("/api/reviews", methods=["POST"])
def add_review():
    data = request.json
    try:
        db = get_db(); cur = db.cursor(dictionary=True)

        book_id = data.get("book_id")

        if not book_id:
            book_name = data.get("book_name", "").strip()
            if not book_name:
                return jsonify({"success": False, "message": "Provide book_id or book_name"}), 400
            cur.execute("SELECT Book_id FROM Book WHERE Title = %s", (book_name,))
            book = cur.fetchone()
            if not book:
                cur.close(); db.close()
                return jsonify({"success": False,
                                "message": f"No book found with name '{book_name}'"}), 404
            book_id = book["Book_id"]

        rating = data.get("rating")
        if rating is None or not (1 <= int(rating) <= 5):
            return jsonify({"success": False, "message": "Rating must be between 1 and 5"}), 400

        cur.execute("""
            INSERT INTO Review (User_id, Book_id, Rating, Comment, Date)
            VALUES (%s, %s, %s, %s, %s)
        """, (data["user_id"], book_id, int(rating),
              data.get("comment", ""), date.today()))
        db.commit()
        cur.close(); db.close()
        return jsonify({"success": True, "message": "Review submitted successfully"})

    except mysql.connector.IntegrityError:
        return jsonify({"success": False,
                        "message": "You have already reviewed this book"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------------- Search Books by Name ----------------
@app.route("/api/books/by-name", methods=["GET"])
def book_by_name():
    try:
        title = request.args.get("title", "").strip()
        if not title:
            return jsonify({"success": False, "message": "title param required"}), 400
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT b.Book_id, b.Title, b.Author,
                   u.Name AS Owner, u.City
            FROM Book b
            JOIN BookOwner bo ON b.Book_id = bo.Book_id
            JOIN User u ON bo.Owner_id = u.User_id
            WHERE b.Title LIKE %s
        """, (f"%{title}%",))
        data = cur.fetchall()
        cur.close(); db.close()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------------- Server Start ----------------
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 BookShare API Running at http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True)