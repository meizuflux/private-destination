from app.utils.auth import OAuthProvider, OAuthUrls, AuthorizationUrl, User


class GithubProvider(OAuthProvider):
    name = "GitHub"
    urls = OAuthUrls(
        authorization=AuthorizationUrl(
            "https://github.com/login/oauth/authorize",
            True,
            {
                "scope": "user:email",
                "allow_signup": "false"
            }
        ),
        token="https://github.com/login/oauth/access_token",
        user="https://api.github.com/user"
    )

    @staticmethod
    def parse_data(data) -> User:
        return {
            "id": str(data["id"]),
            "name": data["login"],
            "email": data["email"],
            "avatar_url": data["avatar_url"]
        }
