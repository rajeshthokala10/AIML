"""
Script: creates data/sample.db — a SQLite database with 6 tables and 100+ rows.

FK chain (4 hops deep):
    users → orders → order_items → products → categories

Also:
    users → reviews → products

Run from project root:
    python scripts/create_sample_db.py
"""

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship

DB_PATH = ROOT / "data" / "sample.db"


# ── ORM Models ────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    parent_category_id = Column(Integer, ForeignKey("categories.category_id"), nullable=True)

    products = relationship("Product", back_populates="category")
    children = relationship("Category", backref="parent", remote_side=[category_id])


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(120), nullable=False, unique=True)
    full_name = Column(String(150))
    created_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    orders = relationship("Order", back_populates="user")
    reviews = relationship("Review", back_populates="user")


class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    stock_qty = Column(Integer, nullable=False, default=0)
    category_id = Column(Integer, ForeignKey("categories.category_id"), nullable=False)
    created_at = Column(DateTime, nullable=False)

    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    reviews = relationship("Review", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    order_date = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False)
    total_amount = Column(Float, nullable=False)
    shipping_address = Column(Text)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.order_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Review(Base):
    __tablename__ = "reviews"

    review_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    rating = Column(Integer, nullable=False)
    title = Column(String(200))
    body = Column(Text)
    created_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="reviews")
    product = relationship("Product", back_populates="reviews")


# ── Seed Data ─────────────────────────────────────────────────────────────────

CATEGORY_DATA = [
    (None, "Electronics", "Gadgets, devices, and accessories"),
    (None, "Clothing", "Apparel for men, women, and children"),
    (None, "Books", "Fiction, non-fiction, and educational titles"),
    (1, "Smartphones", "Mobile phones and accessories"),
    (1, "Laptops", "Portable computers and peripherals"),
    (2, "Men's Wear", "Shirts, trousers, and outerwear"),
    (2, "Women's Wear", "Dresses, tops, and accessories"),
    (3, "Fiction", "Novels and short stories"),
    (3, "Technical Books", "Programming, engineering, and science"),
]

PRODUCT_DATA = [
    # Electronics → Smartphones (category_id=4)
    ("iPhone 15 Pro", "Latest Apple smartphone with A17 chip", 999.99, 120, 4),
    ("Samsung Galaxy S24", "Android flagship with AI features", 849.99, 85, 4),
    ("Google Pixel 8", "Pure Android experience with AI camera", 699.99, 60, 4),
    # Electronics → Laptops (category_id=5)
    ("MacBook Pro 14\"", "Apple M3 Pro chip, 18GB RAM", 1999.99, 45, 5),
    ("Dell XPS 15", "Intel Core i9, OLED display", 1749.99, 30, 5),
    ("ThinkPad X1 Carbon", "Business ultrabook, 12th gen Intel", 1399.99, 55, 5),
    # Clothing → Men's Wear (category_id=6)
    ("Classic Oxford Shirt", "100% cotton formal shirt", 49.99, 200, 6),
    ("Slim Fit Chinos", "Stretch twill trousers", 59.99, 150, 6),
    ("Merino Wool Sweater", "Lightweight knit pullover", 89.99, 90, 6),
    # Clothing → Women's Wear (category_id=7)
    ("Floral Wrap Dress", "Lightweight summer dress", 69.99, 180, 7),
    ("Cropped Blazer", "Tailored fit, lined", 119.99, 70, 7),
    ("High-Rise Jeans", "Straight leg, stretch denim", 79.99, 140, 7),
    # Books → Fiction (category_id=8)
    ("The Midnight Library", "Matt Haig — a story of possibilities", 14.99, 300, 8),
    ("Project Hail Mary", "Andy Weir — survival in deep space", 16.99, 250, 8),
    ("Lessons in Chemistry", "Bonnie Garmus — 1960s chemistry and cooking", 15.99, 220, 8),
    # Books → Technical (category_id=9)
    ("Clean Code", "Robert C. Martin — software craftsmanship", 39.99, 180, 9),
    ("Designing Data-Intensive Applications", "Martin Kleppmann", 54.99, 120, 9),
    ("The Pragmatic Programmer", "Hunt & Thomas — 20th anniversary edition", 44.99, 160, 9),
]

FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Hiro",
               "Isla", "James", "Karen", "Liam", "Maya", "Noah", "Olivia", "Peter",
               "Quinn", "Rosa", "Sam", "Tina", "Uma", "Victor", "Wendy", "Xavi",
               "Yara", "Zoe"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
              "Davis", "Wilson", "Taylor", "Anderson", "Thomas", "Jackson", "White",
              "Harris", "Martin", "Thompson", "Young", "Lee", "Walker"]

ORDER_STATUSES = ["pending", "shipped", "delivered", "delivered", "delivered", "cancelled"]

REVIEW_TITLES = [
    "Great product!", "Highly recommend", "Good value for money",
    "Exceeded expectations", "Decent but could be better",
    "Not what I expected", "Solid purchase", "Five stars",
    "Would buy again", "Amazing quality",
]

REVIEW_BODIES = [
    "Really happy with this purchase. Works exactly as described.",
    "Shipped quickly and the quality is excellent. Will definitely buy again.",
    "Good product overall but the packaging could be improved.",
    "Exactly what I needed. Great build quality.",
    "A bit pricey but worth every penny.",
    "Arrived on time and in perfect condition. Highly recommended.",
    "The quality is top notch. Very satisfied.",
    "Does the job well. Nothing extraordinary but reliable.",
]


def rand_date(days_back: int = 730) -> datetime:
    return datetime.now() - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


def main():
    random.seed(42)

    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    Base.metadata.create_all(engine)

    with Session(engine) as session:

        # ── Categories ────────────────────────────────────────────────────
        categories = []
        for parent_idx, name, desc in CATEGORY_DATA:
            parent_id = categories[parent_idx - 1].category_id if parent_idx else None
            cat = Category(name=name, description=desc, parent_category_id=parent_id)
            session.add(cat)
            session.flush()
            categories.append(cat)
        print(f"  Inserted {len(categories)} categories")

        # ── Products ──────────────────────────────────────────────────────
        products = []
        for name, desc, price, stock, cat_idx in PRODUCT_DATA:
            p = Product(
                name=name,
                description=desc,
                price=price,
                stock_qty=stock,
                category_id=categories[cat_idx - 1].category_id,
                created_at=rand_date(900),
            )
            session.add(p)
            session.flush()
            products.append(p)
        print(f"  Inserted {len(products)} products")

        # ── Users (50) ────────────────────────────────────────────────────
        users = []
        used_usernames = set()
        for i in range(50):
            fn = random.choice(FIRST_NAMES)
            ln = random.choice(LAST_NAMES)
            base = f"{fn.lower()}.{ln.lower()}"
            username = base
            counter = 1
            while username in used_usernames:
                username = f"{base}{counter}"
                counter += 1
            used_usernames.add(username)

            u = User(
                username=username,
                email=f"{username}@example.com",
                full_name=f"{fn} {ln}",
                created_at=rand_date(730),
                is_active=random.random() > 0.1,
            )
            session.add(u)
            session.flush()
            users.append(u)
        print(f"  Inserted {len(users)} users")

        # ── Orders + OrderItems (80 orders, 1-4 items each) ───────────────
        order_count = 0
        item_count = 0
        for _ in range(80):
            user = random.choice(users)
            order_date = rand_date(365)
            items_data = []
            total = 0.0

            for _ in range(random.randint(1, 4)):
                product = random.choice(products)
                qty = random.randint(1, 5)
                subtotal = round(product.price * qty, 2)
                items_data.append((product, qty, subtotal))
                total += subtotal

            order = Order(
                user_id=user.user_id,
                order_date=order_date,
                status=random.choice(ORDER_STATUSES),
                total_amount=round(total, 2),
                shipping_address=f"{random.randint(1,999)} Main St, City, ST {random.randint(10000,99999)}",
            )
            session.add(order)
            session.flush()
            order_count += 1

            for product, qty, subtotal in items_data:
                item = OrderItem(
                    order_id=order.order_id,
                    product_id=product.product_id,
                    quantity=qty,
                    unit_price=product.price,
                    subtotal=subtotal,
                )
                session.add(item)
                item_count += 1

        print(f"  Inserted {order_count} orders, {item_count} order items")

        # ── Reviews (120) ─────────────────────────────────────────────────
        review_count = 0
        seen_pairs = set()
        attempts = 0
        while review_count < 120 and attempts < 500:
            attempts += 1
            user = random.choice(users)
            product = random.choice(products)
            pair = (user.user_id, product.product_id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            r = Review(
                user_id=user.user_id,
                product_id=product.product_id,
                rating=random.randint(1, 5),
                title=random.choice(REVIEW_TITLES),
                body=random.choice(REVIEW_BODIES),
                created_at=rand_date(365),
            )
            session.add(r)
            review_count += 1

        print(f"  Inserted {review_count} reviews")

        session.commit()

    # Row count summary
    from sqlalchemy import text
    with engine.connect() as conn:
        total_rows = 0
        for tbl in ["categories", "users", "products", "orders", "order_items", "reviews"]:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            print(f"    {tbl}: {count} rows")
            total_rows += count
        print(f"  Total rows: {total_rows}")

    print(f"\nDatabase created: {DB_PATH}")


if __name__ == "__main__":
    main()
