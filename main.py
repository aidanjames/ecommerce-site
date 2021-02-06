from flask import Flask, render_template, redirect, url_for, flash, abort, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, load_only
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from forms import CreateProductForm, CreateCustomerForm, LogInForm
from functools import wraps
import os
from datetime import datetime
from flask_bootstrap import Bootstrap

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
Bootstrap(app)

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
    description = db.Column(db.String(129), nullable=False)
    price = db.Column(db.Float, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

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
    in_cart = db.session.query(Purchase).filter(Purchase.purchaser_id == current_user.get_id(),
                                                Purchase.paid is not True)
    user_pur_ids = [pur.id for pur in in_cart]

    purchased_by_others = db.session.query(Purchase).filter(Purchase.purchaser_id != current_user.get_id())
    other_pur_ids = [pur.id for pur in purchased_by_others]

    # Reduce the list of available products that are not reserved/purchased by others
    products_reduced = [product for product in Product.query.all() if product.id not in other_pur_ids]
    return render_template("index.html", all_products=products_reduced, current_user=current_user, in_cart=user_pur_ids)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = CreateCustomerForm()
    if form.validate_on_submit():
        if db.session.query(Customer).filter_by(email=form.email.data).first():
            flash("Email already exists, log in!")
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
            flash("Email not registered, please try again.")
            return redirect(url_for("login"))
        elif not check_password_hash(customer.password, form.password.data):
            flash("Invalid password, please try again.")
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
    return render_template("cart.html")


@app.route("/add-to-cart")
def add_to_cart():
    product_id = request.args.get("product_id")
    print(f"The product id is {product_id}")
    if not current_user.is_anonymous:
        # Add new purchase
        purchase = Purchase(paid=False, purchaser_id=current_user.get_id(), product_id=product_id)
        db.session.add(purchase)
        db.session.commit()
        return redirect(url_for("product_page"))
    return redirect(url_for('login'))


@app.route("/new-product", methods=["GET", "POST"])
@admin_only
def add_new_product():
    form = CreateProductForm()
    if form.validate_on_submit():
        new_product = Product(
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
def delete_post(product_id):
    product_to_delete = Product.query.get(product_id)
    db.session.delete(product_to_delete)
    db.session.commit()
    return redirect(url_for('product_page'))


@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
