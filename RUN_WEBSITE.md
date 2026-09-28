# Run Text Muse Website

From this folder:

```powershell
.\run_website.ps1
```

Or double-click:

```text
run_website.bat
```

Then open:

```text
http://127.0.0.1:8000
```

If port 8000 is already occupied, the launcher automatically uses `http://127.0.0.1:8001`.

The script uses the existing Python environment in `C:\Users\Jaslyn\Desktop\model\.venv` when it is available.

## Firebase backend authentication

The frontend uses Firebase email/password authentication. For production backend token verification, set one of these environment variables before starting the server:

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\firebase-service-account.json"
```

`FIREBASE_SERVICE_ACCOUNT_FILE` is also supported by this project.

For local UI-only testing, use the explicit development bypass instead:

```powershell
$env:FIREBASE_LOCAL_AUTH_BYPASS = "1"
```

Do not enable the bypass on a deployed server.
