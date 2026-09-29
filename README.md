# Campus Cart — Flask E-Commerce Application

A complete, beginner-friendly academic e-commerce application. It uses Flask, SQLite, Flask-SQLAlchemy, Flask-Login, HTML/CSS, and vanilla JavaScript Fetch API.

## Features

- Secure registration, login, logout, hashed passwords, and session authentication.
- User and Admin roles with protected pages and APIs.
- Product catalogue, details page, stock visibility, responsive interface.
- Per-user cart with stock-aware add, update, and remove actions.
- Checkout collects name/address/phone, creates immutable order items, deducts stock, and clears the cart.
- Users only see their own orders; administrators can update all order statuses.
- Admin dashboard and product CRUD UI.
- JSON REST APIs with validation and appropriate status codes.

## Installation and run

```bash
cd ecommerce_project
py -m venv .venv
.venv\Scripts\activate          # Windows PowerShell
py -m pip install -r requirements.txt
py app.py
```

Open `http://127.0.0.1:5000` in a browser. The SQLite database is automatically made at `instance/store.db` on first run, together with four products.

## Accounts

- Register a normal user through `/register`.
- Seeded administrator: `admin@example.com` / `Admin@123`.

The admin dashboard is at `/admin` after admin login.

## User and admin permissions

| Capability | User | Admin |
|---|---:|---:|
| Browse products | Yes | Yes |
| Cart / checkout / own orders | Yes | No customer cart UI |
| Admin dashboard and product CRUD | No | Yes |
| View/update all orders | No | Yes |

Server-side decorators and API checks enforce these permissions; changing navigation links in a browser cannot bypass them.

## Database structure

- `User`: username, email, `password_hash`, role, creation date. One user has cart items and orders.
- `Product`: name, description, price, category, stock, image URL, creation date.
- `CartItem`: user/product/quantity, unique per user and product.
- `Order`: user, total, status, customer name, address, phone, creation date.
- `OrderItem`: order snapshot of product ID, name, price, and quantity. This preserves purchase history when a product changes.

## REST API

| Method | Endpoint | Access |
|---|---|---|
| GET | `/api/products` | Public |
| GET | `/api/products/<id>` | Public |
| POST | `/api/products` | Admin |
| PUT | `/api/products/<id>` | Admin |
| DELETE | `/api/products/<id>` | Admin |
| POST | `/api/cart` | Logged-in user |
| PUT / DELETE | `/api/cart/<item_id>` | Cart owner |
| GET | `/api/orders` | Logged-in user's orders |
| POST | `/api/orders` | Logged-in user, creates order from cart |
| GET | `/api/orders/<id>` | Order owner or admin |
| PUT | `/api/orders/<id>` | Admin; JSON `{ "status": "Shipped" }` |

Product create/update JSON requires `name`, `description`, `price`, `category`, `stock` and `image`. Order creation JSON requires `customer_name`, `address`, and `phone`.

### Product images

While adding or editing a product as an administrator, fill in **Image URL**. For a local image, copy it into `static/images/` and enter a path such as `/static/images/laptop.jpg`. A complete `https://` URL also works. If left empty, the app shows a category initial instead.

## Project structure

```text
ecommerce_project/
├── app.py                 # Flask routes, API, authentication, seeding
├── models.py              # SQLAlchemy data models and relationships
├── requirements.txt
├── README.md
├── instance/store.db      # Created automatically
├── templates/             # Customer and administrator pages
└── static/
    ├── css/style.css      # Responsive styling and media queries
    └── js/script.js       # Fetch-based dynamic operations
```
