from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, TextAreaField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pc_store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ================= MODEL-ები (მონაცემთა ბაზა) =================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    product = db.relationship('Product')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= FORM-ები (WTForms) =================
class RegisterForm(FlaskForm):
    username = StringField('მომხმარებლის სახელი', validators=[DataRequired(), Length(min=4, max=150)])
    password = PasswordField('პაროლი', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('რეგისტრაცია')

class LoginForm(FlaskForm):
    username = StringField('მომხმარებლის სახელი', validators=[DataRequired()])
    password = PasswordField('პაროლი', validators=[DataRequired()])
    submit = SubmitField('შესვლა')

class ProductForm(FlaskForm):
    name = StringField('პროდუქტის სახელი', validators=[DataRequired()])
    description = TextAreaField('აღწერა', validators=[DataRequired()])
    price = FloatField('ფასი (₾)', validators=[DataRequired()])
    submit = SubmitField('დამატება')

# ================= ROUTE-ები (გვერდები და ფუნქციები) =================
@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # 1. ვამოწმებთ, არსებობს თუ არა უკვე ეს სახელი ბაზაში
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('ეს სახელი უკვე დაკავებულია, გთხოვთ აირჩიოთ სხვა.', 'danger')
            return redirect(url_for('register'))
        
        # 2. თუ არ არსებობს, ვაგრძელებთ ჩვეულებრივ რეგისტრაციას
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        is_first_user = User.query.count() == 0
        new_user = User(username=form.username.data, password=hashed_password, is_admin=is_first_user)
        db.session.add(new_user)
        db.session.commit()
        flash('რეგისტრაცია წარმატებულია! შეგიძლიათ გაიაროთ ავტორიზაცია.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('არასწორი სახელი ან პაროლი.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_admin:
        flash('თქვენ არ გაქვთ ამ გვერდზე წვდომის უფლება.', 'danger')
        return redirect(url_for('index'))
    
    form = ProductForm()
    if form.validate_on_submit():
        new_product = Product(name=form.name.data, description=form.description.data, price=form.price.data)
        db.session.add(new_product)
        db.session.commit()
        flash('პროდუქტი წარმატებით დაემატა!', 'success')
        return redirect(url_for('index'))
    return render_template('add_product.html', form=form)

@app.route('/add_to_cart/<int:product_id>')
@login_required
def add_to_cart(product_id):
    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        item.quantity += 1
    else:
        new_item = CartItem(user_id=current_user.id, product_id=product_id)
        db.session.add(new_item)
    db.session.commit()
    flash('პროდუქტი დამატებულია კალათაში! 🛒', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/cart')
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_price = sum(item.product.price * item.quantity for item in items)
    return render_template('cart.html', items=items, total_price=total_price)

@app.route('/checkout')
@login_required
def checkout():
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('გილოცავთ! გადახდა წარმატებით შესრულდა. პროდუქცია მალე გამოიგზავნება! 🎉', 'success')
    return redirect(url_for('index'))

# ================= სერვერის გაშვება =================
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')