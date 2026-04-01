from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta

db = SQLAlchemy()

class Book(db.Model):
    __tablename__ = 'books'
    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(255), nullable=False)
    author        = db.Column(db.String(255), nullable=False)
    isbn          = db.Column(db.String(20), unique=True, nullable=True)
    genre         = db.Column(db.String(100), nullable=True)
    publisher     = db.Column(db.String(200), nullable=True)
    year          = db.Column(db.Integer, nullable=True)
    total_copies  = db.Column(db.Integer, default=1)
    avail_copies  = db.Column(db.Integer, default=1)
    description   = db.Column(db.Text, nullable=True)
    cover_color   = db.Column(db.String(20), default='#c9a84c')
    rating        = db.Column(db.Float, nullable=True)       # 0.0 – 5.0
    is_bestseller = db.Column(db.Boolean, default=False)
    editions      = db.Column(db.Integer, nullable=True)     # number of editions released
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    transactions  = db.relationship('Transaction', backref='book', lazy=True,
                                     cascade='all, delete-orphan')

    @property
    def wikipedia_url(self):
        """Generate a Wikipedia search URL for the author."""
        if not self.author:
            return None
        query = self.author.strip().replace(' ', '_')
        return f"https://en.wikipedia.org/wiki/{query}"

    def to_dict(self):
        return {
            'id':            self.id,
            'title':         self.title,
            'author':        self.author,
            'isbn':          self.isbn,
            'genre':         self.genre,
            'publisher':     self.publisher,
            'year':          self.year,
            'total_copies':  self.total_copies,
            'avail_copies':  self.avail_copies,
            'description':   self.description,
            'cover_color':   self.cover_color,
            'rating':        self.rating,
            'is_bestseller': self.is_bestseller,
            'editions':      self.editions,
            'wikipedia_url': self.wikipedia_url,
            'created_at':    self.created_at.isoformat(),
        }


class Member(db.Model):
    __tablename__ = 'members'
    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(200), nullable=False)
    email           = db.Column(db.String(200), unique=True, nullable=False)
    phone           = db.Column(db.String(30), nullable=True)
    address         = db.Column(db.String(400), nullable=True)
    membership_date = db.Column(db.Date, default=date.today)
    is_active       = db.Column(db.Boolean, default=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    transactions    = db.relationship('Transaction', backref='member', lazy=True,
                                       cascade='all, delete-orphan')

    def to_dict(self):
        active_borrows = Transaction.query.filter_by(
            member_id=self.id, status='borrowed').count()
        return {
            'id':               self.id,
            'name':             self.name,
            'email':            self.email,
            'phone':            self.phone,
            'address':          self.address,
            'membership_date':  self.membership_date.isoformat(),
            'is_active':        self.is_active,
            'active_borrows':   active_borrows,
            'created_at':       self.created_at.isoformat(),
        }


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id          = db.Column(db.Integer, primary_key=True)
    book_id     = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    member_id   = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    borrow_date = db.Column(db.Date, default=date.today)
    due_date    = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date, nullable=True)
    status      = db.Column(db.String(20), default='borrowed')  # borrowed | returned | overdue
    fine_amount = db.Column(db.Float, default=0.0)
    notes       = db.Column(db.String(400), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def compute_status(self):
        if self.return_date:
            return 'returned'
        if date.today() > self.due_date:
            return 'overdue'
        return 'borrowed'

    def compute_fine(self, rate_per_day=2.0):
        if self.return_date and self.return_date > self.due_date:
            days = (self.return_date - self.due_date).days
        elif not self.return_date and date.today() > self.due_date:
            days = (date.today() - self.due_date).days
        else:
            days = 0
        return round(days * rate_per_day, 2)

    def to_dict(self):
        return {
            'id':          self.id,
            'book_id':     self.book_id,
            'book_title':  self.book.title if self.book else None,
            'book_author': self.book.author if self.book else None,
            'member_id':   self.member_id,
            'member_name': self.member.name if self.member else None,
            'borrow_date': self.borrow_date.isoformat(),
            'due_date':    self.due_date.isoformat(),
            'return_date': self.return_date.isoformat() if self.return_date else None,
            'status':      self.compute_status(),
            'fine_amount': self.compute_fine(),
            'notes':       self.notes,
            'created_at':  self.created_at.isoformat(),
        }
