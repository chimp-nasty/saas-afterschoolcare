from tests.factories import Api


# After logging in, the session endpoint reports who you are: the customer's
# email and their 'customer' role.
def test_login_sets_session(api: Api, customer):
    response = customer.client.get("/auth/v1/session")

    assert response.status_code == 200
    assert response.json()["data"]["email"] == customer.email
    assert response.json()["data"]["roles"] == ["customer"]


# Logging in with the wrong password is refused (401).
def test_login_wrong_password(api: Api, customer):
    response = api.client().post(
        "/auth/v1/login/location1",
        json={"email": customer.email, "password": "wrong-password"},
    )

    assert response.status_code == 401


# A user can only log in at a location where they have a role: the customer
# belongs to location1, so logging in at location2 is refused.
def test_login_at_location_without_a_role(api: Api, customer):
    # The customer only has a role at location1.
    response = api.client().post(
        "/auth/v1/login/location2",
        json={"email": customer.email, "password": customer.password},
    )

    assert response.status_code == 401


# Logging out ends the session, so the session endpoint then says you're not
# logged in (401).
def test_logout_ends_session(customer):
    assert customer.client.post("/auth/v1/logout").status_code == 200

    assert customer.client.get("/auth/v1/session").status_code == 401


# A client that never logged in has no session (401).
def test_no_session_without_login(api: Api):
    assert api.client().get("/auth/v1/session").status_code == 401


# Requesting a password reset for a registered email creates exactly one
# reset token for that user.
def test_forgot_password_creates_token_for_known_email(api: Api, customer):
    response = api.client().post(
        "/auth/v1/forgot-password",
        json={"email": customer.email},
    )

    assert response.status_code == 200

    rows = api.sql(
        """
        SELECT count(*) FROM auth.password_reset_tokens t
        JOIN auth.users u ON u.id = t.user_id
        WHERE u.email = :email
        """,
        email=customer.email,
    )
    assert rows[0][0] == 1


# Requesting a reset for an unregistered email gets exactly the same answer
# as for a registered one, so the endpoint can't be used to find out which
# emails have accounts.
def test_forgot_password_does_not_reveal_unknown_email(api: Api, customer):
    # Separate clients: the endpoint is rate limited per client.
    known = api.client().post(
        "/auth/v1/forgot-password",
        json={"email": customer.email},
    )
    unknown = api.client().post(
        "/auth/v1/forgot-password",
        json={"email": "nobody@test.com"},
    )

    assert unknown.status_code == known.status_code == 200
    assert unknown.json() == known.json()


# A reset token sets a new password that can then be used to log in, and the
# same token can't be used a second time.
def test_reset_password_round_trip(api: Api, customer):
    token = api.reset_token(customer.email)
    new_password = "NewPassword456"

    response = api.client().post(
        "/auth/v1/reset-password",
        json={"token": token, "password": new_password},
    )
    assert response.status_code == 200

    # The new password works...
    api.login(customer.email, new_password)

    # ...and the token can't be used again.
    response = api.client().post(
        "/auth/v1/reset-password",
        json={"token": token, "password": "AnotherPassword789"},
    )
    assert response.status_code == 400


# Resetting a password with a made-up token is refused (400).
def test_reset_password_rejects_unknown_token(api: Api):
    response = api.client().post(
        "/auth/v1/reset-password",
        json={"token": "not-a-real-token", "password": "Password123"},
    )

    assert response.status_code == 400


# The forgot-password endpoint allows 5 requests per minute per client; the
# 6th is refused with 429 too many requests.
def test_forgot_password_is_rate_limited(api: Api):
    client = api.client()

    statuses = [
        client.post(
            "/auth/v1/forgot-password",
            json={"email": "nobody@test.com"},
        ).status_code
        for _ in range(6)
    ]

    # 5 per minute per client.
    assert statuses == [200] * 5 + [429]
