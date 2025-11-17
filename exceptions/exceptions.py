class UserNotFoundException(Exception):
    pass

class PostNotFoundException(Exception):
    pass

class NotOwnerError(Exception):
    pass

class SessionAlreadyClosed(Exception):
    pass