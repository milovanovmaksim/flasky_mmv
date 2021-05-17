# -*- coding: utf-8 -*-
import json
import re
import unittest
from base64 import b64encode

from app import create_app, db
from app.models import User, Role, Post, Comment
from flask import url_for


class APITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()
        self.client = self.app.test_client()


    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def get_auth_headers(self, username, password):
        headers = {
            'Authorization': 'Basic ' + b64encode((username + ':' + password).encode('utf-8')).decode('utf-8'),
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        return headers

    def add_user(self, email, password, confirmed=True, username=None):
        r = Role.query.filter_by(name='User').first()
        self.assertIsNotNone(r)
        user = User(email=email, password=password, confirmed=confirmed, role=r, username=username)
        db.session.add(user)
        db.session.commit()
        return user


    def test_no_auth(self):
        response = self.client.get(url_for('api.get_posts', content_type='application/json'))
        self.assertEqual(response.status_code, 401)

    def test_post(self):
        # добавить пользователя
        email = 'john@example.com'
        password = 'cat'
        user = self.add_user(email=email, password=password)

        # написать пустой пост
        response = self.client.post(url_for('api.new_post'),
                                    headers=self.get_auth_headers('john@example.com', 'cat'),
                                    data=json.dumps({'body': ''}))
        self.assertTrue(response.status_code == 400)

        # новый пост
        response = self.client.post(url_for('api.new_post'),
                                    headers=self.get_auth_headers('john@example.com', 'cat'),
                                    data=json.dumps({'body': 'testing API'}))

        self.assertTrue(response.status_code == 201)
        url = response.headers.get('Location')
        self.assertIsNotNone(url)

        # получить новый пост (только что добавленный)
        response = self.client.get(url, headers=self.get_auth_headers('john@example.com', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['url'] == url)
        self.assertTrue(json_response['body'] == 'testing API')
        self.assertTrue(json_response['body_html'] == '<p>testing API</p>')
        json_post = json_response

        # получить пост по user id
        response = self.client.get(url_for('api.get_user_posts', id=user.id),
                                   headers=self.get_auth_headers(email, password))
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.data)
        self.assertIsNotNone(json_response.get('posts'))
        self.assertEqual(json_response.get('count', 0), 1)
        self.assertEqual(json_response['posts'][0], json_post)


        # get the post from the user as a follower
        response = self.client.get(url_for('api.get_user_followed_posts', id=user.id),
                                   headers=self.get_auth_headers(email, password))
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.get_data(as_text=True))
        self.assertIsNotNone(json_response.get('posts'))
        self.assertEqual(json_response.get('count', 0), 0)
        self.assertEqual(json_response['posts'], [])

        # редактирование постов
        response = self.client.put(url, headers=self.get_auth_headers(email, password),
                                   data = json.dumps({'body': 'updated body'}))
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.data)
        self.assertEqual(json_response['url'], url)
        self.assertEqual(json_response['body'], 'updated body')
        self.assertEqual(json_response['body_html'], '<p>updated body</p>')

    def test_404(self):
        email = 'john@example.com'
        password = 'cat'
        self.add_user(email=email, password=password)

        response = self.client.get('/wrong/url', headers=self.get_auth_headers(email, password))
        self.assertEqual(response.status_code, 404)
        json_response = json.loads(response.data)
        self.assertEqual(json_response['error'], 'not found')

    def test_bad_auth(self):
        email = 'john@example.com'
        password = 'cat'
        self.add_user(email=email, password=password)

        # аутентификация с неверным паролем
        response = self.client.get(url_for('api.get_posts'),
                                   headers=self.get_auth_headers(username=email, password='dog'))
        self.assertEqual(response.status_code, 401)

    def test_token_auth(self):
        email = 'john@example.com'
        password = 'cat'
        self.add_user(email=email, password=password)

        # запрос с неверным токен
        response = self.client.get(url_for('api.get_posts'),
                                   headers=self.get_auth_headers(username='bad-token', password=''))
        self.assertEqual(response.status_code, 401)

        # получить токен
        response = self.client.post(url_for('api.get_token'), headers=self.get_auth_headers(email, password))
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.data)
        self.assertIsNotNone(json_response.get('token'))
        token = json_response['token']

        # запрос с токеном
        response = self.client.get(url_for('api.get_posts'),
                                   headers=self.get_auth_headers(username=token, password=''))
        self.assertEqual(response.status_code, 200)

    def test_anonymous(self):
        response = self.client.get(url_for('api.get_posts'), headers=self.get_auth_headers('', ''))
        self.assertEqual(response.status_code, 401)

    def test_unconfirmed_account(self):
        # добавим не подтвержденного пользователя
        email = 'john@example.com'
        password = 'cat'
        self.add_user(email=email, password=password, confirmed=False)

        # получить посты неподтвержденным аккаунтом
        response = self.client.get(url_for('api.get_posts'), headers=self.get_auth_headers(email, password))
        self.assertEqual(response.status_code, 403)


    def test_users(self):
        # добавить двух пользователей
        user_1 = self.add_user(email='john@example.com', username='john', password='cat')
        user_2 = self.add_user(email='susan@example.com', username='susan', password='dog')

        # получить пользователей
        response = self.client.get(url_for('api.get_user', id=user_2.id),
                                   headers = self.get_auth_headers('john@example.com', 'cat'))
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.data)
        self.assertEqual(json_response['username'], 'susan')

        response = self.client.get(url_for('api.get_user', id=user_1.id),
                                   headers = self.get_auth_headers('susan@example.com', 'dog'))
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.data)
        self.assertEqual(json_response['username'], 'john')

    def test_comment(self):
        # добавить двух пользователей
        user_1 = self.add_user(email='john@example.com', username='john', password='cat')
        user_2 = self.add_user(email='susan@example.com', username='susan', password='dog')

        # добавим пост
        post = Post(body='body of the post', author=user_1)
        db.session.add(post)
        db.session.commit()

        # написать комментарий к посту
        response = self.client.post(url_for('api.new_post_comment', id=post.id),
                                    headers=self.get_auth_headers('susan@example.com', 'dog'),
                                    data=json.dumps({'body': 'Good [post](http://example.com)!'}))
        self.assertEqual(response.status_code, 201)
        json_response = json.loads(response.data)
        post_url = response.headers.get('Location')
        self.assertIsNotNone(post_url)
        self.assertEqual(json_response['body'], 'Good [post](http://example.com)!')
        self.assertEqual(re.sub('<.*?>', '', json_response['body_html']), 'Good post!')

        # получить новый комментарий
        response = self.client.get(post_url, headers=self.get_auth_headers('john@example.com', 'cat'))
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.data)
        self.assertEqual(json_response['url'], post_url)
        self.assertEqual(json_response['body'], 'Good [post](http://example.com)!')

        # добавить еще один комментарий
        comment = Comment(body='Thank you!', author=user_1, post=post)
        db.session.add(comment)
        db.session.commit()

        # получить все комментарии
        response = self.client.get(url_for('api.get_post_comments',  id=post.id),
                                   headers=self.get_auth_headers('susan@example.com', 'dog'))
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.data)
        self.assertIsNotNone(json_response.get('comments'))
        self.assertEqual(json_response.get('count', 0), 2)






