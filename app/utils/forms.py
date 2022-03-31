from webargs.aiohttpparser import AIOHTTPParser

class RaiseErrorParser(AIOHTTPParser):
    def handle_error(self, err, *_, **__):
        raise err

parser = RaiseErrorParser()