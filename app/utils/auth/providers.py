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
            "id": int(data["id"]),
            "username": data["login"],
            "email": data["email"],
            "avatar_url": data["avatar_url"]
        }

class DiscordProvider(OAuthProvider):
    name = "Discord"
    urls = OAuthUrls(
        authorization=AuthorizationUrl(
            "https://discord.com/api/oauth2/authorize",
            True,
            {
                "scope": "identify email",
                "response_type": "code"
            }
        ),
        token="https://discord.com/api/oauth2/token",
        user="https://discord.com/api/users/@me"
    )

    @staticmethod
    def parse_data(data) -> User:
        if data["avatar"] is None:
            avatar_url = f"https://cdn.discordapp.com/embed/avatars/{data['discriminator'] % 5}.png"
        else:
            avatar_url = f"https://cdn.discordapp.com/avatars/{data['id']}/{data['avatar']}.png?size=64"
        return {
            "id": int(data["id"]),
            "username": data["username"],
            "email": data.get("email"),
            "avatar_url": avatar_url
        }

providers = {
    "github": GithubProvider,
    "discord": DiscordProvider
}
