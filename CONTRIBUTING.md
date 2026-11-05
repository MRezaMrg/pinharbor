# Contributing / مشارکت

Thank you for helping improve PinHarbor. لطفاً برای بهبود نرم‌افزار از Issue و Pull Request استفاده کنید.

## Before coding / پیش از شروع

1. Search existing issues first / ابتدا Issueهای قبلی را بررسی کنید.
2. For larger features, open a feature request describing behavior, UX and scope / برای قابلیت‌های بزرگ، پیشنهاد جداگانه ثبت کنید.
3. Never include downloads, credentials, browser cookies, proxy secrets or archives / فایل رسانه، کوکی و اطلاعات حساب را Commit نکنید.

## Development / توسعه

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Keep the legacy `QSettings("PinterestBoardStudio", "Desktop")` key and `.pinterest-studio` archive compatible when changing user-facing branding. Test source-upgrade and rollback when changing installation files. Add regression tests for bug fixes. Changes to the downloader should avoid shell concatenation and preserve URL validation.

## Pull requests / پول‌ریکوئست

Describe the problem, solution, affected versions, tests, and visible UI changes. For screenshots, redact any personal information. A Windows smoke test is required before claiming production-ready Windows downloads.

We may decline changes that bypass authentication or access controls, collect session credentials without user intent, or enable unauthorized redistribution of copyrighted content.
