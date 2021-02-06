from flask import Flask, render_template, redirect, url_for, flash, abort, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from forms import CreateProductForm, CreateCustomerForm, LogInForm
from functools import wraps
import os
from datetime import datetime
from flask_bootstrap import Bootstrap
import stripe

stripe.api_key = os.getenv("STRIPE_API_KEY")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
Bootstrap(app)

MY_DOMAIN = "https://treeme-ajp.herokuapp.com"

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///shop.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)


# CONFIGURE TABLES
class Customer(UserMixin, db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))

    # Relationships
    purchases = relationship("Purchase", back_populates="purchaser")


class Purchase(db.Model):
    __tablename__ = "purchases"
    id = db.Column(db.Integer, primary_key=True)
    paid = db.Column(db.Boolean, nullable=False)

    # Relationships
    purchaser_id = db.Column(db.Integer, db.ForeignKey("customers.id"))
    purchaser = relationship("Customer", back_populates="purchases")
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    product = relationship("Product", back_populates="purchase")


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(129), nullable=False)
    price = db.Column(db.Float, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(50), nullable=True)

    # Relationships
    purchase = relationship("Purchase", back_populates="product")


db.create_all()


@login_manager.user_loader
def user_loader(customer_id):
    return db.session.query(Customer).get(customer_id)


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_anonymous:
            return abort(403)
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def product_page():
    if not current_user.is_anonymous:
        in_cart = db.session.query(Purchase).filter(Purchase.purchaser_id == current_user.id, Purchase.paid is not True)
        in_cart = [pur.product_id for pur in in_cart]
        purchased_by_others = db.session.query(Purchase).filter(Purchase.purchaser_id != current_user.id)
        other_pur_ids = [pur.product_id for pur in purchased_by_others]
        products_reduced = [product for product in Product.query.all() if product.id not in other_pur_ids]
    else:
        in_cart = []
        all_purchases_product_id = [purchase.product_id for purchase in Purchase.query.all()]
        products_reduced = [product for product in Product.query.all() if product.id not in all_purchases_product_id]
    return render_template("index.html", all_products=products_reduced, current_user=current_user, in_cart=in_cart)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = CreateCustomerForm()
    if form.validate_on_submit():
        if db.session.query(Customer).filter_by(email=form.email.data).first():
            flash("Email already exists, log in!", "error")
            return redirect(url_for("login"))

        hashed_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )

        new_customer = Customer()
        new_customer.email = form.email.data
        new_customer.name = form.name.data
        new_customer.password = hashed_password

        db.session.add(new_customer)
        db.session.commit()

        login_user(new_customer)
        return redirect(url_for("product_page"))

    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LogInForm()
    if form.validate_on_submit():
        customer = db.session.query(Customer).filter_by(email=form.email.data).first()
        if not customer:
            flash("Email not registered, please try again or register for a new account.", "error")
            return redirect(url_for("login"))
        elif not check_password_hash(customer.password, form.password.data):
            flash("Invalid password, please try again.", "error")
            return redirect(url_for("login"))
        else:
            login_user(customer)
            return redirect(url_for("product_page"))

    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('product_page'))


@app.route("/cart")
def cart():
    if current_user.is_anonymous:
        return redirect(url_for('login'))

    # Work out what products are in the cart and send it to the template
    in_cart = db.session.query(Purchase).filter(Purchase.purchaser_id == current_user.id, Purchase.paid is not True)
    in_cart = [pur.product_id for pur in in_cart]
    products_in_cart = [product for product in Product.query.all() if product.id in in_cart]
    total_price = 0
    for product in products_in_cart:
        total_price += product.price
    return render_template("cart.html", purchases=products_in_cart, total=total_price)


@app.route("/add-to-cart")
def add_to_cart():
    product_id = request.args.get("product_id")
    if not current_user.is_anonymous:
        # Add new purchase
        purchase = Purchase(paid=False, purchaser_id=current_user.get_id(), product_id=product_id)
        db.session.add(purchase)
        db.session.commit()
        return redirect(url_for("product_page"))
    flash("You need to log in to start shopping.", "error")
    return redirect(url_for('login'))


@app.route("/delete-from-cart")
def delete_from_cart():
    product_id = request.args.get("product_id")
    purchase = db.session.query(Purchase).filter(Purchase.product_id == product_id).first()
    if purchase:
        db.session.delete(purchase)
        db.session.commit()
    return redirect(url_for('cart'))


@app.route("/new-product", methods=["GET", "POST"])
@admin_only
def add_new_product():
    form = CreateProductForm()
    if form.validate_on_submit():
        new_product = Product(
            title=form.title.data,
            description=form.description.data,
            price=form.price.data,
            img_url=form.img_url.data
        )
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for("product_page"))
    return render_template("new-product.html", form=form, current_user=current_user)


@app.route("/delete/<int:product_id>")
@admin_only
def delete_product(product_id):
    product_to_delete = Product.query.get(product_id)
    db.session.delete(product_to_delete)
    db.session.commit()
    return redirect(url_for('product_page'))


@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    in_cart = db.session.query(Purchase).filter(Purchase.purchaser_id == current_user.id, Purchase.paid is not True)
    print(in_cart)
    in_cart = [pur.product_id for pur in in_cart]
    print(in_cart)
    products_in_cart = [product for product in Product.query.all() if product.id in in_cart]
    print(products_in_cart)
    line_items = []
    for product in products_in_cart:
        amt = int(product.price * 100)
        new_item = {
            "price_data": {
                "currency": "gbp",
                "unit_amount": amt,
                "product_data": {
                    "name": product.title,
                    "images": [product.img_url],
                },
            },
            "quantity": 1,
        }
        line_items.append(new_item)
    print(line_items)

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url=MY_DOMAIN + "/success",
            cancel_url=MY_DOMAIN + "/cancel",
        )
        thing_to_return = jsonify({"id": checkout_session.id})
        print(thing_to_return)
        return thing_to_return
    except Exception as e:
        print(f"We've got an exception...{e}")
        return jsonify(error=str(e)), 403


@app.route("/success")
def success():
    # TODO Email customer and set purchase to paid.
    return render_template("success.html")

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
