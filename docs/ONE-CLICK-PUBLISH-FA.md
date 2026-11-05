# انتشار PinHarbor در GitHub — مسیر کوتاه

## مرحله ۱ — دریافت بسته درست

فایل **`PinHarbor-v2.5.0-GitHub-Repository.zip`** را دانلود و در یک پوشه مستقل استخراج کنید. این بسته فقط سورس و فایل‌های انتشار را دارد و شامل فایل EXE آماده نیست. نیاز نیست مخزن جدیدی را دستی با README یا License مقداردهی کنید.

## مرحله ۲ — پیش‌نیازهای یک‌باره

روی ویندوز **Python 3.10+**، [Git](https://git-scm.com/downloads) و [GitHub CLI](https://cli.github.com/) را نصب کنید. سپس در ترمینال:

```powershell
gh auth login
git config --global user.name "YOUR-NAME"
git config --global user.email "YOUR-PUBLIC-EMAIL"
```

برای اینکه ایمیل شخصی در کامیت‌ها دیده نشود، می‌توانید از نشانی `noreply` خود GitHub استفاده کنید. لازم نیست توکن یا رمز را داخل فایل‌های این پروژه قرار دهید.

## مرحله ۳ — انتشار سورس با یک فایل

فایل **`Publish to GitHub.bat`** را اجرا کنید، نام مخزن (به‌صورت `pinharbor` یا `OWNER/pinharbor`) و عمومی/خصوصی بودن را انتخاب کنید و برای تأیید نهایی عبارت `PUBLISH` را بنویسید. اسکریپت ابتدا فهرست کنترل‌شده فایل‌ها را Stage و Commit می‌کند و با GitHub CLI ریپازیتوری را ایجاد و Push می‌کند. رسانه‌های دانلودشده، فایل‌های موقت، تنظیمات و کوکی‌ها انتخاب نمی‌شوند.

اگر قصد بررسی بدون انتشار دارید:

```powershell
python tools/github_publish.py --repo pinharbor
```

انتشار واقعی بدون تأیید اجرا نمی‌شود:

```powershell
python tools/github_publish.py --repo pinharbor --execute
```

*هشدار:* آپلود عمومی، کد و سوابق کامیت‌های Stageشده را عمومی می‌کند. پیش از تأیید، نام، مجوز و محتوای مخزن را بررسی کنید.

## مرحله ۴ — دریافت نسخه ویندوز

در GitHub به تب **Actions** بروید؛ گردش‌کار `Test, package and draft release` باید تست‌ها، تست اولیه GUI و ساخت ZIP ویندوز را انجام دهد. در اجرای موفق branch `main` می‌توان خروجی ZIP را از **Artifacts** دریافت کرد. انتشار واقعی EXE در این محیط از پیش تست نشده است.

## مرحله ۵ — ساخت Release رسمی، بعد از تست دستی

بعد از تست واقعی روی Windows 10/11 و یک بورد شامل تصویر/ویدیو، از مخزن محلی Tag بسازید:

```powershell
git tag v2.5.0
git push origin v2.5.0
```

این دستور ساخت Release **پیش‌نویس (Draft)** را فعال می‌کند. فایل‌ها را بررسی و سپس در GitHub آن را Publish کنید؛ خودکار عمومی نمی‌شود. نام نسخه و Tag باید یکسان باشند. راهنمای QA در `docs/RELEASE-CHECKLIST.md` است.

## نصب برای کاربران

کاربران عادی باید از بخش **Releases** فایل **`PinHarbor-v2.5.0-Windows-portable.zip`** را دریافت کنند، ZIP را کامل Extract کنند و `PinHarbor.exe` را از داخل پوشه `PinHarbor` باز کنند. آن‌ها به Python نیازی ندارند؛ اما این بسته فقط پس از ساخت موفق در CI موجود خواهد بود.

برای آپدیت نصب‌های **سورسی** نسخه‌های پیشین، از بسته `UPDATE.zip` و فایل `Upgrade Existing Installation.bat` استفاده کنید. فایل Update برای نصب EXE مناسب نیست. هنگام به‌روزرسانی برنامه قبلی باید بسته باشد.
