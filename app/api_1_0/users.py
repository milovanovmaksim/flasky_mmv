from flask import jsonify, request, current_app, url_for

from . import api
from app.models import User, Post


@api.route('/user/<int:id>')
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify(user.to_json())


@api.route('/users/<int:id>/posts')
def get_user_posts(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['FLASKY_POSTS_PER_PAGE']
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(page, per_page, error_out=True)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_user_posts', id=id, page=page-1)
    next_page = None
    if pagination.has_next:
        next_page = url_for('api.get_user_posts', id=id, page=page+1)
    return jsonify({
        'posts': [post.to_json() for post in posts],
        'prev': prev,
        'next': next_page,
        'count': pagination.total
    })


@api.route('/users/<int:id>/timeline/')
def get_user_followed_posts(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['FLASKY_POSTS_PER_PAGE']
    pagination = user.followed_posts.order_by(Post.timestamp.desc()).paginate(page, per_page, error_out=True)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_user_followed_posts', id=id, page=page-1)
    next_page = None
    if pagination.has_next:
        next_page = url_for('api.get_user_followed_posts', id=id, page=page+1)
    return jsonify({
        'posts': [post.to_json() for post in posts],
        'prev': prev,
        'next': next_page,
        'count': pagination.total
    })


