# Indic AAC Studio accounts

Login: http://localhost:8000/login
Signup: http://localhost:8000/signup

Demo username: `demo`
Demo password: `AACdemo@2026`

The demo account is shared and has no special permissions. Use Signup to create a private local account, or Continue with Google to use your Google/Gmail identity. Successful signup or login opens the AAC system. A sign-out button revokes the backend session and returns to login. Local accounts need a username (letters/numbers plus . _ @ + -), a display name, and a password of at least 8 characters. Local registration is not email verification. Google sign-in uses the existing Firebase project and requires network access, Google provider enabled and localhost in Authorized domains. Actual Google verification uses the existing backend verifier; Google credentials are not stored locally.

Account data is stored in the existing Redis database under the aac:v1 namespace. Passwords use salted scrypt hashes. Local and Google identities have separate account data. HTTP-only cookies identify sessions; writes to personal data retain CSRF protection. Login/signup are rate limited by client address. Redis AOF persistence remains enabled by run_local.py. The default account is created once when signup/login is first used, and is included in new portable installs through application code, not by shipping the source machine database.

The offline static demo has no real authentication. Its personal data stays in the browser and it retains the 80-sentence recorded gallery. The full live application opens its normal AAC interface after login and does not display that gallery.
