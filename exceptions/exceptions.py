class UserNotFoundException(Exception):
    pass

class PostNotFoundException(Exception):
    pass

class NotOwnerError(Exception):
    pass

class SessionAlreadyClosed(Exception):
    pass

class ReportNotFoundException(Exception):
    pass

class ReportAlreadyReviewedException(Exception):
    pass
    
class ChatNotFoundException(Exception):
    pass

class ChatAlreadyExistsException(Exception):
    pass

class ChatClosedException(Exception):
    pass