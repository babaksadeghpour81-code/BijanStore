class AppState:
    access_token = None
    refresh_token = None
    username = None

    @classmethod
    def set_tokens(cls, access, refresh, username):
        cls.access_token = access
        cls.refresh_token = refresh
        cls.username = username

    @classmethod
    def clear(cls):
        cls.access_token = None
        cls.refresh_token = None
        cls.username = None

    @classmethod
    def is_logged_in(cls):
        return cls.access_token is not None