from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from sqlalchemy import ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
# from flask_gravatar import Gravatar
from functools import wraps
from flask import abort
import smtplib

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

my_email = "pythondevelopmenttestingemail@gmail.com"
password = "hcmfmnnlrtmiuice"

##CONFIGURE TABLES
with app.app_context():
    class BlogPost(db.Model):
        __tablename__ = "blog_posts"
        id = db.Column(db.Integer, primary_key=True)
        author = db.Column(db.String(250), nullable=False)
        title = db.Column(db.String(250), unique=True, nullable=False)
        subtitle = db.Column(db.String(250), nullable=False)
        date = db.Column(db.String(250), nullable=False)
        body = db.Column(db.Text, nullable=False)
        img_url = db.Column(db.String(250), nullable=False)
        comments = db.relationship('Comment', backref='blog_post')

    class User(UserMixin, db.Model):
        __tablename__ = "User"
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(100), unique=True)
        password = db.Column(db.String(100))
        name = db.Column(db.String(1000))
        comments = db.relationship('Comment', backref='user')

    class Comment(db.Model):
        __tablename__ = "comments"
        id = db.Column(db.Integer, primary_key=True)
        comment = db.Column(db.Text)
        user_id = db.Column(db.Integer, db.ForeignKey('User.id'))
        post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))

    # db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register',methods=['POST','GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        all_users = User.query.all()[::]
        if all_users:
            for user in all_users:
                if form.email.data == user.email:
                    error = "You have already sign up with that email, login instead"
                    return redirect(url_for('login'))
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8)
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect('/')
    return render_template("register.html",form=form)


@app.route('/login',methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        try:
            user = User.query.filter_by(email=email)[0]
        except:
            error = "This email does not exist, Please try again!"
            return render_template("login.html", message=error, form=form)
        else:
            if not check_password_hash(user.password, password):
                error = "Password incorrect, Please try again!"
                return render_template("login.html", message=error,form=form)
            elif check_password_hash(user.password, password):
                login_user(user)
                return redirect('/')
    return render_template("login.html",form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=['GET','POST'])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    comments = Comment.query.all()[::]
    commented_users = [User.query.get(i.user_id).name for i in comments]
    combined_list = list(zip(comments, commented_users))
    length = len(combined_list)
    emails = [User.query.get(i.user_id).email for i in comments]
    if form.validate_on_submit():
        if current_user.is_anonymous:
            error = "Please login or register to comment"
            return render_template('post.html',  post=requested_post, message=error, form=form,combined_list=combined_list,length=length,emails=emails)
        else:
            comment = Comment(
                comment=form.comment.data,
                user_id=current_user.id,
                post_id=post_id,
            )
            db.session.add(comment)
            db.session.commit()
            success = "Your comment has been submitted"
            return render_template('post.html',  post=requested_post,form=form, message=success,combined_list=combined_list,length=length,emails=emails)
    return render_template("post.html", post=requested_post,form=form,comments=comments,combined_list=combined_list,length=length,emails=emails)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact",methods=['POST','GET'])
def contact():
    if request.method == 'POST':
        name = request.values.get('name'),
        email = request.values.get('email'),
        phonenum = request.values.get('phone'),
        message = request.values.get('message'),
        with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
            connection.starttls()
            connection.login(user=my_email, password=password)
            connection.sendmail(
                from_addr=my_email,
                to_addrs="prathipatisuhas050@gmail.com",
                msg=f"Subject: New Blog Contact\n\nName: {name}\nEmail: {email}\nPhone: {phonenum}\nMessage: {message}"
            )
        return redirect('/contact')
    return render_template('contact.html')



@app.route("/new-post", methods=['GET', 'POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=form.author.data,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))

    return render_template("make-post.html", form=form,is_edit=False)



@app.route("/edit-post/<int:post_id>",methods=['GET','POST'])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)
