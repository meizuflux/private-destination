from webargs.aiohttpparser import AIOHTTPParser


class RaiseErrorParser(AIOHTTPParser):
    def handle_error(self, err, *_, **__) -> None:
        raise err


parser = RaiseErrorParser()
