class AuthService:
    def login(self, credentials):
        return {
            'token': 'mock-jwt-token',
            'user': {
                'id': 1,
                'email': credentials.get('email')
            }
        }

    def signup(self, user_data):
        return {
            'id': 2,
            **user_data
        }

class UserService:
    def get_user(self, user_id):
        return {
            'id': user_id,
            'name': 'John Doe',
            'email': 'john@example.com'
        }

    def list_users(self):
        return [
            {'id': 1, 'name': 'John Doe'},
            {'id': 2, 'name': 'Jane Doe'}
        ]

    def update_profile(self, user_id, data):
        return {
            'id': user_id,
            **data,
            'updated': True
        }
