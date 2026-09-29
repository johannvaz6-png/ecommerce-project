import os
from datetime import timezone, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Product, CartItem, Order, OrderItem

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-secret-key-before-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'store.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
os.makedirs(app.instance_path, exist_ok=True)
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'

@login_manager.user_loader
def load_user(user_id): return db.session.get(User, int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/api/'):
        return jsonify(error='Authentication required.'), 401
    return redirect(url_for('login', next=request.url))

def is_admin(): return current_user.is_authenticated and current_user.role == 'Admin'
def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated: return login_manager.unauthorized()
        if not is_admin(): abort(403)
        return view(*args, **kwargs)
    return wrapped
def api_error(message, status=400): return jsonify(error=message), status
def product_data(p):
    return {'id':p.id,'name':p.name,'description':p.description,'price':float(p.price),'category':p.category,'stock':p.stock,'image':p.image or '','created_at':p.created_at.isoformat()}
def order_data(o):
    return {'id':o.id,'user_id':o.user_id,'total_amount':float(o.total_amount),'status':o.status,'customer_name':o.customer_name,'address':o.address,'phone':o.phone,'created_at':o.created_at.isoformat(),'items':[{'id':i.id,'product_id':i.product_id,'product_name':i.product_name,'price':float(i.price),'quantity':i.quantity} for i in o.items]}
def parse_product(data):
    required = ['name','description','price','category','stock']
    if not all(str(data.get(k, '')).strip() for k in required): raise ValueError('Name, description, price, category, and stock are required.')
    try:
        price, stock = Decimal(str(data['price'])), int(data['stock'])
    except (InvalidOperation, ValueError): raise ValueError('Price must be a number and stock must be a whole number.')
    if price < 0 or stock < 0: raise ValueError('Price and stock cannot be negative.')
    return {'name':str(data['name']).strip(), 'description':str(data['description']).strip(), 'price':price, 'category':str(data['category']).strip(), 'stock':stock, 'image':str(data.get('image','')).strip()}
def cart_total(items): return sum((item.product.price * item.quantity for item in items), Decimal('0.00'))

@app.template_filter('ist')
def format_ist(value):
    """Display stored UTC timestamps in Indian Standard Time."""
    return value.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30))).strftime('%d %b %Y, %I:%M %p')

@app.template_filter('inr')
def format_inr(value):
    """Format a numeric value as whole Indian rupees, e.g. 125000 -> 1,25,000."""
    amount = int(Decimal(value).quantize(Decimal('1')))
    digits = str(abs(amount))
    if len(digits) > 3:
        tail, head = digits[-3:], digits[:-3]
        groups = []
        while head:
            groups.append(head[-2:])
            head = head[:-2]
        digits = ','.join(reversed(groups)) + ',' + tail
    return ('-' if amount < 0 else '') + digits

@app.route('/')
def index(): return render_template('index.html')
@app.route('/products/<int:product_id>')
def product_detail(product_id): return render_template('product_detail.html', product= db.get_or_404(Product, product_id))
@app.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        username, email, password = request.form.get('username','').strip(), request.form.get('email','').strip().lower(), request.form.get('password','')
        if not username or not email or len(password) < 6: flash('Username, email, and a password of at least 6 characters are required.', 'error')
        elif User.query.filter((User.username == username) | (User.email == email)).first(): flash('That username or email is already registered.', 'error')
        else:
            db.session.add(User(username=username,email=email,password_hash=generate_password_hash(password)))
            db.session.commit(); flash('Registration complete. Please log in.', 'success'); return redirect(url_for('login'))
    return render_template('register.html')
@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email','').strip().lower()).first()
        if user and check_password_hash(user.password_hash, request.form.get('password','')):
            login_user(user); flash('Welcome back!', 'success'); return redirect(request.args.get('next') or url_for('index'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')
@app.route('/logout')
@login_required
def logout(): logout_user(); flash('You have been logged out.', 'success'); return redirect(url_for('index'))
@app.route('/cart')
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    return render_template('cart.html', items=items, total=cart_total(items))
@app.route('/checkout', methods=['GET','POST'])
@login_required
def checkout():
    items=CartItem.query.filter_by(user_id=current_user.id).all()
    if not items: flash('Your cart is empty.', 'error'); return redirect(url_for('cart'))
    if request.method == 'POST':
        name,address,phone=(request.form.get(k,'').strip() for k in ('customer_name','address','phone'))
        if not name or not address or not phone: flash('Name, address, and phone are required.', 'error')
        else:
            for item in items:
                if item.quantity > item.product.stock: flash(f'{item.product.name} no longer has enough stock.', 'error'); return redirect(url_for('cart'))
            order=Order(user_id=current_user.id,total_amount=cart_total(items),customer_name=name,address=address,phone=phone)
            db.session.add(order); db.session.flush()
            for item in items:
                db.session.add(OrderItem(order_id=order.id,product_id=item.product.id,product_name=item.product.name,price=item.product.price,quantity=item.quantity)); item.product.stock -= item.quantity; db.session.delete(item)
            db.session.commit(); return redirect(url_for('order_confirmation', order_id=order.id))
    return render_template('checkout.html', items=items, total=cart_total(items))
@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc(), Order.id.desc()).all()
    order_numbers = {order.id: len(user_orders) - index for index, order in enumerate(user_orders)}
    return render_template('orders.html', orders=user_orders, order_numbers=order_numbers)
@app.route('/orders/<int:order_id>/confirmation')
@login_required
def order_confirmation(order_id):
    order=db.get_or_404(Order,order_id)
    if order.user_id != current_user.id and not is_admin(): abort(403)
    user_order_number = Order.query.filter(Order.user_id == current_user.id, Order.id <= order.id).count()
    return render_template('order_confirmation.html', order=order, user_order_number=user_order_number)
@app.route('/admin')
@admin_required
def admin_dashboard(): return render_template('admin_dashboard.html', products=Product.query.count(), orders=Order.query.count(), pending=Order.query.filter_by(status='Pending').count(), users=User.query.filter_by(role='User').count())
@app.route('/admin/products')
@admin_required
def manage_products(): return render_template('manage_products.html', products=Product.query.order_by(Product.id.asc()).all())
@app.route('/admin/orders')
@admin_required
def manage_orders(): return render_template('manage_orders.html', orders=Order.query.order_by(Order.created_at.desc()).all(), statuses=['Pending','Processing','Shipped','Delivered','Cancelled'])

@app.route('/api/products')
def api_products(): return jsonify(products=[product_data(p) for p in Product.query.order_by(Product.created_at.desc()).all()])
@app.route('/api/products/<int:product_id>')
def api_product(product_id):
    p=db.session.get(Product, product_id)
    return api_error('Product not found.',404) if not p else jsonify(product=product_data(p))
@app.route('/api/products', methods=['POST'])
@admin_required
def api_add_product():
    try: values=parse_product(request.get_json(silent=True) or request.form); p=Product(**values); db.session.add(p); db.session.commit(); return jsonify(product=product_data(p)),201
    except ValueError as e: return api_error(str(e))
@app.route('/api/products/<int:product_id>', methods=['PUT'])
@admin_required
def api_update_product(product_id):
    p=db.session.get(Product,product_id)
    if not p:return api_error('Product not found.',404)
    try:
        for k,v in parse_product(request.get_json(silent=True) or {}).items(): setattr(p,k,v)
        db.session.commit(); return jsonify(product=product_data(p))
    except ValueError as e:return api_error(str(e))
@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@admin_required
def api_delete_product(product_id):
    p=db.session.get(Product,product_id)
    if not p:return api_error('Product not found.',404)
    if p.cart_items:return api_error('Cannot delete a product that is in a cart.',409)
    db.session.delete(p);db.session.commit();return jsonify(message='Product deleted.')
@app.route('/api/cart', methods=['POST'])
@login_required
def api_add_cart():
    data=request.get_json(silent=True) or {}; p=db.session.get(Product,data.get('product_id'))
    try:q=int(data.get('quantity',1))
    except (TypeError,ValueError):q=0
    if not p:return api_error('Product not found.',404)
    if q < 1:return api_error('Quantity must be at least 1.')
    item=CartItem.query.filter_by(user_id=current_user.id,product_id=p.id).first(); new_q=q+(item.quantity if item else 0)
    if new_q > p.stock:return api_error('Requested quantity exceeds available stock.')
    if item:item.quantity=new_q
    else:db.session.add(CartItem(user_id=current_user.id,product_id=p.id,quantity=q))
    db.session.commit();return jsonify(message='Added to cart.')
@app.route('/api/cart/<int:item_id>', methods=['PUT','DELETE'])
@login_required
def api_cart_item(item_id):
    item=CartItem.query.filter_by(id=item_id,user_id=current_user.id).first()
    if not item:return api_error('Cart item not found.',404)
    if request.method=='DELETE':db.session.delete(item);db.session.commit();return jsonify(message='Item removed.')
    try:q=int((request.get_json(silent=True) or {}).get('quantity'))
    except (ValueError,TypeError):q=0
    if q < 1:return api_error('Quantity must be at least 1.')
    if q > item.product.stock:return api_error('Requested quantity exceeds available stock.')
    item.quantity=q;db.session.commit();return jsonify(message='Cart updated.')
@app.route('/api/orders', methods=['GET','POST'])
@login_required
def api_orders():
    if request.method=='GET':return jsonify(orders=[order_data(o) for o in Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()])
    data=request.get_json(silent=True) or {}; items=CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:return api_error('Your cart is empty.')
    if not all(str(data.get(k,'')).strip() for k in ('customer_name','address','phone')):return api_error('Customer name, address, and phone are required.')
    for item in items:
        if item.quantity > item.product.stock:return api_error(f'Insufficient stock for {item.product.name}.',409)
    order=Order(user_id=current_user.id,total_amount=cart_total(items),customer_name=data['customer_name'].strip(),address=data['address'].strip(),phone=data['phone'].strip());db.session.add(order);db.session.flush()
    for item in items: db.session.add(OrderItem(order_id=order.id,product_id=item.product.id,product_name=item.product.name,price=item.product.price,quantity=item.quantity));item.product.stock-=item.quantity;db.session.delete(item)
    db.session.commit();return jsonify(order=order_data(order)),201
@app.route('/api/orders/<int:order_id>', methods=['GET','PUT'])
@login_required
def api_order(order_id):
    order=db.session.get(Order,order_id)
    if not order:return api_error('Order not found.',404)
    if request.method=='GET':
        if order.user_id != current_user.id and not is_admin():return api_error('You are not allowed to view this order.',403)
        return jsonify(order=order_data(order))
    if not is_admin():return api_error('Admin access required.',403)
    status=(request.get_json(silent=True) or {}).get('status','')
    if status not in ['Pending','Processing','Shipped','Delivered','Cancelled']:return api_error('Invalid order status.')
    order.status=status;db.session.commit();return jsonify(order=order_data(order))

@app.errorhandler(403)
def forbidden(error):
    if request.path.startswith('/api/'): return api_error('You do not have permission to perform this action.',403)
    return render_template('error.html', code=403, message='You do not have permission to access this page.'),403
@app.errorhandler(404)
def missing(error):
    if request.path.startswith('/api/'): return api_error('Resource not found.',404)
    return render_template('error.html', code=404, message='The page you requested was not found.'),404

def seed_database():
    if not User.query.filter_by(email='admin@example.com').first(): db.session.add(User(username='admin',email='admin@example.com',password_hash=generate_password_hash('Admin@123'),role='Admin'))
    if not Product.query.first(): db.session.add_all([Product(name='Laptop Pro',description='Reliable laptop for study and work.',price=Decimal('59999.00'),category='Electronics',stock=8,image=''),Product(name='Smartphone X',description='Modern smartphone with a bright display.',price=Decimal('34999.00'),category='Electronics',stock=12,image=''),Product(name='Wireless Headphones',description='Comfortable noise-isolating headphones.',price=Decimal('2499.00'),category='Audio',stock=20,image=''),Product(name='Running Shoes',description='Lightweight shoes for everyday movement.',price=Decimal('1999.00'),category='Fashion',stock=15,image='')])
    db.session.commit()
with app.app_context(): db.create_all(); seed_database()
if __name__ == '__main__': app.run(debug=True)
