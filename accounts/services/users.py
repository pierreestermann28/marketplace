from accounts.forms import SignUpForm


def create_user_from_signup(*, form: SignUpForm):
    return form.save()
