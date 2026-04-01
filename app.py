import os
from flask import Flask, jsonify, request, render_template, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import date, timedelta, datetime
from sqlalchemy import or_, func

from models import db, Book, Member, Transaction

def create_app():
    app = Flask(__name__)
    CORS(app)

    # ── Database config ──────────────────────────────────────────────
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_url = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(base_dir, 'library.db')}"
    )
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')

    db.init_app(app)

    with app.app_context():
        db.create_all()
        seed_demo_data()

    # ── Groq chatbot (lazy init so missing key doesn't crash startup) ──
    _groq_client = None

    def get_groq_client():
        nonlocal _groq_client
        if _groq_client is None:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return None
            try:
                from groq import Groq
                _groq_client = Groq(api_key=api_key)
            except Exception as e:
                print("Groq init error:", e)
                return None
        return _groq_client

    def ask_groq_for_books(user_message, books):
        client = get_groq_client()
        if client is None:
            return "⚠️ Chatbot is not configured. Please set the GROQ_API_KEY environment variable in your Render dashboard."
        try:
            book_info = ""
            for b in books:
                bestseller = " [BESTSELLER]" if b.get('is_bestseller') else ""
                rating = f" | Rating: {b['rating']}/5" if b.get('rating') else ""
                editions = f" | Editions: {b['editions']}" if b.get('editions') else ""
                book_info += f"- {b['title']} by {b['author']} ({b['year']}){bestseller}{rating}{editions}\n"

            prompt = f"""You are a friendly and knowledgeable library assistant.

The user is interacting with a library management system.
Only recommend books from the available books list below.
Give a short 2-line review for each recommended book.
Mention if a book is a bestseller or its rating when relevant.

User Question:
{user_message}

Available Books:
{book_info}

Give a friendly, helpful, and concise response."""

            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant"
            )
            return chat_completion.choices[0].message.content

        except Exception as e:
            print("Groq Error:", e)
            return f"Sorry, I couldn't process your request right now. Please try again later."

    @app.route("/chatbot", methods=["POST"])
    def chatbot():
        data = request.get_json() or {}
        user_message = data.get("message", "").strip()
        if not user_message:
            return jsonify({"response": "Please ask me something about the books!"}), 400

        books_db = Book.query.all()
        books = [
            {
                "title": b.title,
                "author": b.author,
                "year": b.year,
                "genre": b.genre,
                "rating": b.rating,
                "is_bestseller": b.is_bestseller,
                "editions": b.editions,
                "avail_copies": b.avail_copies,
            }
            for b in books_db
        ]

        response = ask_groq_for_books(user_message, books)
        return jsonify({"response": response})

    # ── Frontend ─────────────────────────────────────────────────────
    @app.route('/')
    def index():
        return render_template('index.html')

    # ── DASHBOARD ────────────────────────────────────────────────────
    @app.route('/api/dashboard')
    def dashboard():
        today = date.today()

        total_books   = Book.query.count()
        total_members = Member.query.filter_by(is_active=True).count()
        borrowed      = Transaction.query.filter_by(status='borrowed').count()
        overdue_q     = [t for t in Transaction.query.filter_by(return_date=None).all()
                         if today > t.due_date]
        overdue       = len(overdue_q)

        chart = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            cnt = Transaction.query.filter(Transaction.borrow_date == d).count()
            chart.append({'date': d.isoformat(), 'count': cnt})

        recent = [t.to_dict() for t in
                  Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()]

        genres = db.session.query(
            Book.genre, func.count(Book.id).label('count')
        ).filter(Book.genre.isnot(None)).group_by(Book.genre)\
         .order_by(func.count(Book.id).desc()).limit(5).all()

        return jsonify({
            'stats': {
                'total_books':   total_books,
                'total_members': total_members,
                'borrowed':      borrowed,
                'overdue':       overdue,
            },
            'chart':   chart,
            'recent':  recent,
            'genres':  [{'genre': g, 'count': c} for g, c in genres],
        })

    # ── BOOKS ────────────────────────────────────────────────────────
    @app.route('/api/books', methods=['GET'])
    def list_books():
        q      = request.args.get('q', '').strip()
        genre  = request.args.get('genre', '').strip()
        avail  = request.args.get('available', '').strip()
        page   = int(request.args.get('page', 1))
        per    = int(request.args.get('per_page', 20))

        query = Book.query
        if q:
            like = f'%{q}%'
            query = query.filter(or_(
                Book.title.ilike(like),
                Book.author.ilike(like),
                Book.isbn.ilike(like),
                Book.genre.ilike(like),
            ))
        if genre:
            query = query.filter(Book.genre.ilike(f'%{genre}%'))
        if avail == 'true':
            query = query.filter(Book.avail_copies > 0)

        total   = query.count()
        books   = query.order_by(Book.created_at.desc())\
                       .offset((page - 1) * per).limit(per).all()
        return jsonify({
            'books': [b.to_dict() for b in books],
            'total': total, 'page': page, 'per_page': per,
        })

    @app.route('/api/books', methods=['POST'])
    def add_book():
        data = request.get_json() or {}
        errors = {}
        if not data.get('title'): errors['title'] = 'Title is required'
        if not data.get('author'): errors['author'] = 'Author is required'
        if errors:
            return jsonify({'errors': errors}), 422

        copies = int(data.get('total_copies', 1))
        rating_val = data.get('rating')
        if rating_val is not None and rating_val != '':
            rating_val = float(rating_val)
            rating_val = max(0.0, min(5.0, rating_val))
        else:
            rating_val = None

        book = Book(
            title         = data['title'].strip(),
            author        = data['author'].strip(),
            isbn          = data.get('isbn', '').strip() or None,
            genre         = data.get('genre', '').strip() or None,
            publisher     = data.get('publisher', '').strip() or None,
            year          = int(data['year']) if data.get('year') else None,
            total_copies  = copies,
            avail_copies  = copies,
            description   = data.get('description', '').strip() or None,
            cover_color   = data.get('cover_color', '#c9a84c'),
            rating        = rating_val,
            is_bestseller = bool(data.get('is_bestseller', False)),
            editions      = int(data['editions']) if data.get('editions') else None,
        )
        db.session.add(book)
        db.session.commit()
        return jsonify(book.to_dict()), 201

    @app.route('/api/books/<int:bid>', methods=['GET'])
    def get_book(bid):
        book = Book.query.get_or_404(bid)
        return jsonify(book.to_dict())

    @app.route('/api/books/<int:bid>', methods=['PUT'])
    def update_book(bid):
        book = Book.query.get_or_404(bid)
        data = request.get_json() or {}
        errors = {}
        if 'title' in data and not data['title']: errors['title'] = 'Title is required'
        if 'author' in data and not data['author']: errors['author'] = 'Author is required'
        if errors:
            return jsonify({'errors': errors}), 422

        if 'title'         in data: book.title       = data['title'].strip()
        if 'author'        in data: book.author       = data['author'].strip()
        if 'isbn'          in data: book.isbn         = data['isbn'].strip() or None
        if 'genre'         in data: book.genre        = data['genre'].strip() or None
        if 'publisher'     in data: book.publisher    = data['publisher'].strip() or None
        if 'year'          in data: book.year         = int(data['year']) if data['year'] else None
        if 'description'   in data: book.description  = data['description'].strip() or None
        if 'cover_color'   in data: book.cover_color  = data['cover_color']
        if 'is_bestseller' in data: book.is_bestseller = bool(data['is_bestseller'])
        if 'editions'      in data:
            book.editions = int(data['editions']) if data['editions'] else None
        if 'rating' in data:
            rv = data['rating']
            if rv is not None and rv != '':
                book.rating = max(0.0, min(5.0, float(rv)))
            else:
                book.rating = None
        if 'total_copies' in data:
            new_total = int(data['total_copies'])
            diff = new_total - book.total_copies
            book.avail_copies = max(0, book.avail_copies + diff)
            book.total_copies = new_total

        db.session.commit()
        return jsonify(book.to_dict())

    @app.route('/api/books/<int:bid>', methods=['DELETE'])
    def delete_book(bid):
        book = Book.query.get_or_404(bid)
        active = Transaction.query.filter_by(book_id=bid, return_date=None).count()
        if active:
            return jsonify({'error': 'Cannot delete: book has active borrows'}), 409
        db.session.delete(book)
        db.session.commit()
        return jsonify({'deleted': bid})

    @app.route('/api/genres')
    def genres():
        rows = db.session.query(Book.genre)\
                         .filter(Book.genre.isnot(None))\
                         .distinct().all()
        return jsonify([r[0] for r in rows])

    # ── MEMBERS ──────────────────────────────────────────────────────
    @app.route('/api/members', methods=['GET'])
    def list_members():
        q    = request.args.get('q', '').strip()
        page = int(request.args.get('page', 1))
        per  = int(request.args.get('per_page', 20))

        query = Member.query
        if q:
            like = f'%{q}%'
            query = query.filter(or_(
                Member.name.ilike(like),
                Member.email.ilike(like),
                Member.phone.ilike(like),
            ))

        total   = query.count()
        members = query.order_by(Member.created_at.desc())\
                       .offset((page - 1) * per).limit(per).all()
        return jsonify({
            'members': [m.to_dict() for m in members],
            'total': total,
        })

    @app.route('/api/members', methods=['POST'])
    def add_member():
        data = request.get_json() or {}
        errors = {}
        if not data.get('name'):  errors['name']  = 'Name is required'
        if not data.get('email'): errors['email'] = 'Email is required'
        if errors:
            return jsonify({'errors': errors}), 422

        if Member.query.filter_by(email=data['email'].strip()).first():
            return jsonify({'errors': {'email': 'Email already registered'}}), 422

        member = Member(
            name    = data['name'].strip(),
            email   = data['email'].strip().lower(),
            phone   = data.get('phone', '').strip() or None,
            address = data.get('address', '').strip() or None,
        )
        db.session.add(member)
        db.session.commit()
        return jsonify(member.to_dict()), 201

    @app.route('/api/members/<int:mid>', methods=['GET'])
    def get_member(mid):
        member = Member.query.get_or_404(mid)
        data = member.to_dict()
        data['transactions'] = [t.to_dict() for t in
            Transaction.query.filter_by(member_id=mid)
                             .order_by(Transaction.created_at.desc()).all()]
        return jsonify(data)

    @app.route('/api/members/<int:mid>', methods=['PUT'])
    def update_member(mid):
        member = Member.query.get_or_404(mid)
        data = request.get_json() or {}
        if 'name'      in data: member.name      = data['name'].strip()
        if 'phone'     in data: member.phone     = data['phone'].strip() or None
        if 'address'   in data: member.address   = data['address'].strip() or None
        if 'is_active' in data: member.is_active = bool(data['is_active'])
        db.session.commit()
        return jsonify(member.to_dict())

    @app.route('/api/members/<int:mid>', methods=['DELETE'])
    def delete_member(mid):
        member = Member.query.get_or_404(mid)
        active = Transaction.query.filter_by(member_id=mid, return_date=None).count()
        if active:
            return jsonify({'error': 'Member has unreturned books'}), 409
        db.session.delete(member)
        db.session.commit()
        return jsonify({'deleted': mid})

    # ── TRANSACTIONS ─────────────────────────────────────────────────
    @app.route('/api/transactions', methods=['GET'])
    def list_transactions():
        status    = request.args.get('status', '')
        member_id = request.args.get('member_id', '')
        book_id   = request.args.get('book_id', '')
        page      = int(request.args.get('page', 1))
        per       = int(request.args.get('per_page', 20))

        query = Transaction.query
        if member_id: query = query.filter_by(member_id=int(member_id))
        if book_id:   query = query.filter_by(book_id=int(book_id))

        all_txns = query.order_by(Transaction.created_at.desc()).all()

        if status:
            all_txns = [t for t in all_txns if t.compute_status() == status]

        total = len(all_txns)
        page_txns = all_txns[(page - 1) * per: page * per]
        return jsonify({
            'transactions': [t.to_dict() for t in page_txns],
            'total': total,
        })

    @app.route('/api/transactions/borrow', methods=['POST'])
    def borrow_book():
        data      = request.get_json() or {}
        book_id   = data.get('book_id')
        member_id = data.get('member_id')
        days      = int(data.get('days', 14))
        notes     = data.get('notes', '')

        if not book_id or not member_id:
            return jsonify({'error': 'book_id and member_id required'}), 422

        book   = Book.query.get_or_404(book_id)
        member = Member.query.get_or_404(member_id)

        if book.avail_copies < 1:
            return jsonify({'error': 'No copies available'}), 409
        if not member.is_active:
            return jsonify({'error': 'Member account is inactive'}), 409

        existing = Transaction.query.filter_by(
            book_id=book_id, member_id=member_id, return_date=None).first()
        if existing:
            return jsonify({'error': 'Member already has this book borrowed'}), 409

        txn = Transaction(
            book_id   = book_id,
            member_id = member_id,
            due_date  = date.today() + timedelta(days=days),
            notes     = notes.strip() or None,
        )
        book.avail_copies -= 1
        db.session.add(txn)
        db.session.commit()
        return jsonify(txn.to_dict()), 201

    @app.route('/api/transactions/<int:tid>/return', methods=['POST'])
    def return_book(tid):
        txn = Transaction.query.get_or_404(tid)
        if txn.return_date:
            return jsonify({'error': 'Book already returned'}), 409

        txn.return_date = date.today()
        txn.status      = 'returned'
        txn.fine_amount = txn.compute_fine()
        txn.book.avail_copies = min(txn.book.total_copies,
                                    txn.book.avail_copies + 1)
        db.session.commit()
        return jsonify(txn.to_dict())

    @app.route('/api/transactions/<int:tid>', methods=['DELETE'])
    def delete_transaction(tid):
        txn = Transaction.query.get_or_404(tid)
        if not txn.return_date:
            txn.book.avail_copies = min(txn.book.total_copies,
                                        txn.book.avail_copies + 1)
        db.session.delete(txn)
        db.session.commit()
        return jsonify({'deleted': tid})

    # ── SEARCH (all) ─────────────────────────────────────────────────
    @app.route('/api/search')
    def global_search():
        q = request.args.get('q', '').strip()
        if not q:
            return jsonify({'books': [], 'members': []})
        like = f'%{q}%'
        books = Book.query.filter(or_(
            Book.title.ilike(like), Book.author.ilike(like)
        )).limit(5).all()
        members = Member.query.filter(or_(
            Member.name.ilike(like), Member.email.ilike(like)
        )).limit(5).all()
        return jsonify({
            'books':   [b.to_dict() for b in books],
            'members': [m.to_dict() for m in members],
        })

    return app


# ── SEED DATA ────────────────────────────────────────────────────────
def seed_demo_data():
    if Book.query.count() > 0:
        return

    books = [
        # Fiction
        {'title':'The Great Gatsby','author':'F. Scott Fitzgerald','genre':'Fiction','year':1925,'isbn':'978-0-7432-7356-5','total_copies':3,'cover_color':'#4a7c6a','rating':4.1,'is_bestseller':True,'editions':5,'description':'A portrait of the Jazz Age in all of its decadence and excess.'},
        {'title':'To Kill a Mockingbird','author':'Harper Lee','genre':'Fiction','year':1960,'isbn':'978-0-06-112008-4','total_copies':4,'cover_color':'#8b2635','rating':4.8,'is_bestseller':True,'editions':4,'description':'A gripping tale of racial injustice and childhood innocence in the American South.'},
        {'title':'The Alchemist','author':'Paulo Coelho','genre':'Fiction','year':1988,'isbn':'978-0-06-231609-7','total_copies':3,'cover_color':'#c9a84c','rating':4.2,'is_bestseller':True,'editions':4,'description':'A philosophical novel about following your dreams and listening to your heart.'},
        # Dystopian
        {'title':'1984','author':'George Orwell','genre':'Dystopian','year':1949,'isbn':'978-0-452-28423-4','total_copies':5,'cover_color':'#2c3e50','rating':4.7,'is_bestseller':True,'editions':6,'description':'A chilling depiction of a totalitarian society where Big Brother watches everything.'},
        {'title':'Brave New World','author':'Aldous Huxley','genre':'Dystopian','year':1932,'isbn':'978-0-06-085052-4','total_copies':3,'cover_color':'#34495e','rating':4.1,'is_bestseller':False,'editions':4,'description':'A futuristic society built on pleasure, conformity and the suppression of individuality.'},
        # Romance
        {'title':'Pride and Prejudice','author':'Jane Austen','genre':'Romance','year':1813,'isbn':'978-0-14-143951-8','total_copies':3,'cover_color':'#c0392b','rating':4.5,'is_bestseller':True,'editions':8,'description':'A witty exploration of love, class and marriage in Regency-era England.'},
        {'title':'Me Before You','author':'Jojo Moyes','genre':'Romance','year':2012,'isbn':'978-0-14-312454-1','total_copies':3,'cover_color':'#e91e63','rating':4.3,'is_bestseller':True,'editions':2,'description':'A heartbreaking love story about a woman who changes the life of a quadriplegic man.'},
        # Fantasy
        {'title':'The Hobbit','author':'J.R.R. Tolkien','genre':'Fantasy','year':1937,'isbn':'978-0-547-92822-7','total_copies':4,'cover_color':'#27ae60','rating':4.6,'is_bestseller':True,'editions':7,'description':'Bilbo Baggins is swept into an epic quest to reclaim the lost dwarf kingdom of Erebor.'},
        {'title':"Harry Potter and the Philosopher's Stone",'author':'J.K. Rowling','genre':'Fantasy','year':1997,'isbn':'978-0-7475-3269-9','total_copies':6,'cover_color':'#8e44ad','rating':4.9,'is_bestseller':True,'editions':3,'description':'A young boy discovers he is a wizard and begins his education at Hogwarts.'},
        {'title':'The Name of the Wind','author':'Patrick Rothfuss','genre':'Fantasy','year':2007,'isbn':'978-0-7564-0407-9','total_copies':3,'cover_color':'#16a085','rating':4.5,'is_bestseller':False,'editions':2,'description':'The tale of a legendary wizard told in his own words — a story of love, loss, and magic.'},
        # History
        {'title':'Sapiens','author':'Yuval Noah Harari','genre':'History','year':2011,'isbn':'978-0-06-231609-8','total_copies':2,'cover_color':'#e67e22','rating':4.4,'is_bestseller':True,'editions':2,'description':'A brief history of humankind, from the Stone Age to the modern era.'},
        {'title':'Guns, Germs, and Steel','author':'Jared Diamond','genre':'History','year':1997,'isbn':'978-0-393-31755-8','total_copies':2,'cover_color':'#d68910','rating':4.2,'is_bestseller':True,'editions':3,'description':'Why did some civilisations conquer others? A sweeping account of human history.'},
        # Self-Help
        {'title':'Atomic Habits','author':'James Clear','genre':'Self-Help','year':2018,'isbn':'978-0-7352-1129-2','total_copies':4,'cover_color':'#1abc9c','rating':4.8,'is_bestseller':True,'editions':2,'description':'An easy and proven way to build good habits and break bad ones.'},
        {'title':'The 7 Habits of Highly Effective People','author':'Stephen R. Covey','genre':'Self-Help','year':1989,'isbn':'978-0-7432-6951-3','total_copies':3,'cover_color':'#148f77','rating':4.4,'is_bestseller':True,'editions':5,'description':'Powerful lessons in personal change based on timeless principles.'},
        # Sci-Fi
        {'title':'Dune','author':'Frank Herbert','genre':'Sci-Fi','year':1965,'isbn':'978-0-441-17271-9','total_copies':3,'cover_color':'#d35400','rating':4.3,'is_bestseller':False,'editions':5,'description':'A sweeping tale of politics, religion, ecology and power on a desert planet.'},
        {'title':'The Hitchhiker\'s Guide to the Galaxy','author':'Douglas Adams','genre':'Sci-Fi','year':1979,'isbn':'978-0-345-39180-3','total_copies':4,'cover_color':'#2980b9','rating':4.6,'is_bestseller':True,'editions':4,'description':'An absurdly funny journey through space after Earth is demolished for a bypass.'},
        # Mystery
        {'title':'The Girl with the Dragon Tattoo','author':'Stieg Larsson','genre':'Mystery','year':2005,'isbn':'978-0-307-45454-1','total_copies':3,'cover_color':'#555555','rating':4.2,'is_bestseller':True,'editions':3,'description':'A journalist and a hacker investigate a decades-old disappearance in a wealthy Swedish family.'},
        {'title':'And Then There Were None','author':'Agatha Christie','genre':'Mystery','year':1939,'isbn':'978-0-06-207348-8','total_copies':4,'cover_color':'#7f8c8d','rating':4.5,'is_bestseller':True,'editions':6,'description':'Ten strangers are lured to an island, and one by one they begin to die.'},
        # Thriller
        {'title':'Gone Girl','author':'Gillian Flynn','genre':'Thriller','year':2012,'isbn':'978-0-307-58836-4','total_copies':3,'cover_color':'#c0392b','rating':4.0,'is_bestseller':True,'editions':2,'description':'On their fifth anniversary, Nick Dunne\'s wife Amy disappears — and nothing is what it seems.'},
        {'title':'The Da Vinci Code','author':'Dan Brown','genre':'Thriller','year':2003,'isbn':'978-0-385-50420-5','total_copies':4,'cover_color':'#8b0000','rating':3.9,'is_bestseller':True,'editions':3,'description':'A Harvard symbologist unravels a deadly conspiracy hidden within the works of Leonardo da Vinci.'},
        # Biography
        {'title':'Steve Jobs','author':'Walter Isaacson','genre':'Biography','year':2011,'isbn':'978-1-4516-4853-9','total_copies':2,'cover_color':'#95a5a6','rating':4.3,'is_bestseller':True,'editions':2,'description':'The exclusive biography of Apple co-founder Steve Jobs, based on over 40 interviews.'},
        {'title':'Long Walk to Freedom','author':'Nelson Mandela','genre':'Biography','year':1994,'isbn':'978-0-316-54818-3','total_copies':2,'cover_color':'#196f3d','rating':4.7,'is_bestseller':True,'editions':3,'description':'The autobiography of Nelson Mandela — his journey from rural boy to global icon.'},
        # Philosophy
        {'title':'Meditations','author':'Marcus Aurelius','genre':'Philosophy','year':180,'isbn':'978-0-14-044140-6','total_copies':3,'cover_color':'#6c5ce7','rating':4.6,'is_bestseller':True,'editions':10,'description':'Personal writings of the Roman emperor reflecting on Stoic philosophy and self-improvement.'},
        {'title':'Sophie\'s World','author':'Jostein Gaarder','genre':'Philosophy','year':1991,'isbn':'978-0-374-53087-9','total_copies':2,'cover_color':'#5e35b1','rating':4.1,'is_bestseller':False,'editions':3,'description':'A thrilling journey through the history of philosophy, disguised as a novel.'},
        # Science
        {'title':'A Brief History of Time','author':'Stephen Hawking','genre':'Science','year':1988,'isbn':'978-0-553-38016-3','total_copies':3,'cover_color':'#00b894','rating':4.3,'is_bestseller':True,'editions':4,'description':'From the Big Bang to Black Holes — Hawking explains the universe in accessible terms.'},
        {'title':'The Selfish Gene','author':'Richard Dawkins','genre':'Science','year':1976,'isbn':'978-0-19-857519-1','total_copies':2,'cover_color':'#00897b','rating':4.2,'is_bestseller':False,'editions':4,'description':'Dawkins popularises the gene-centred view of evolution in this landmark work.'},
        # Business
        {'title':'Rich Dad Poor Dad','author':'Robert T. Kiyosaki','genre':'Business','year':1997,'isbn':'978-1-61268-116-2','total_copies':4,'cover_color':'#0984e3','rating':4.0,'is_bestseller':True,'editions':4,'description':'What the rich teach their kids about money that the poor and middle class do not.'},
        {'title':'Zero to One','author':'Peter Thiel','genre':'Business','year':2014,'isbn':'978-0-8041-3929-8','total_copies':3,'cover_color':'#1565c0','rating':4.2,'is_bestseller':True,'editions':2,'description':'Notes on startups, or how to build the future — from a legendary Silicon Valley entrepreneur.'},
        # Psychology
        {'title':'Thinking, Fast and Slow','author':'Daniel Kahneman','genre':'Psychology','year':2011,'isbn':'978-0-374-27563-1','total_copies':3,'cover_color':'#a29bfe','rating':4.5,'is_bestseller':True,'editions':2,'description':'A Nobel laureate explores two systems of thought and the psychology of decision-making.'},
        {'title':'Man\'s Search for Meaning','author':'Viktor E. Frankl','genre':'Psychology','year':1946,'isbn':'978-0-8070-1428-6','total_copies':3,'cover_color':'#7c4dff','rating':4.8,'is_bestseller':True,'editions':6,'description':'A psychiatrist\'s account of his experiences in Nazi concentration camps and his discovery of logotherapy.'},
        # Horror
        {'title':'The Shining','author':'Stephen King','genre':'Horror','year':1977,'isbn':'978-0-307-74365-6','total_copies':3,'cover_color':'#424242','rating':4.4,'is_bestseller':True,'editions':4,'description':'A family heads to an isolated hotel for the winter, where supernatural forces drive the father to madness.'},
        # Classics
        {'title':'Crime and Punishment','author':'Fyodor Dostoevsky','genre':'Classics','year':1866,'isbn':'978-0-14-305814-5','total_copies':2,'cover_color':'#795548','rating':4.5,'is_bestseller':False,'editions':8,'description':'A young man commits a murder and grapples with guilt, morality and redemption in 19th-century Russia.'},
        # Children
        {'title':'The Little Prince','author':'Antoine de Saint-Exupéry','genre':'Children','year':1943,'isbn':'978-0-15-646511-4','total_copies':5,'cover_color':'#ffca28','rating':4.6,'is_bestseller':True,'editions':7,'description':'A poetic tale about a young prince who visits various planets, including Earth, in search of friendship.'},
    ]

    for bdata in books:
        copies = bdata.pop('total_copies')
        b = Book(**bdata, total_copies=copies, avail_copies=copies)
        db.session.add(b)

    members = [
        {'name':'Shivansh Pandey','email':'shivansh.pandey@email.com','phone':'9876543210'},
        {'name':'Shivam Prajapati','email':'shivam.prajapati@email.com','phone':'9123456789'},
        {'name':'Swati Yadav','email':'swati.yadav@email.com','phone':'9988776655'},
        {'name':'Sneha Mehta','email':'sneha.mehta@email.com','phone':'9871234560'},
        {'name':'Arjun Nair','email':'arjun.nair@email.com','phone':'9765432109'},
    ]
    for mdata in members:
        db.session.add(Member(**mdata))

    db.session.commit()


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)