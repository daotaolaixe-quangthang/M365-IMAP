# Microsoft Outlook OAuth token và Graph API demo

Project này dùng Python để lấy OAuth token cho tài khoản Outlook/Microsoft 365 bằng public client ID của Thunderbird, sau đó tái sử dụng refresh token để đọc email qua Microsoft Graph API.

Thunderbird khi đăng nhập Outlook (Microsoft 365/Outlook.com) sử dụng OAuth2 với một Client ID đã được Mozilla đăng ký trên Microsoft Entra ID.

Client ID này là public, bạn có thể xem được bằng cách:
- Mở source của Thunderbird
- Hoặc xem log OAuth
- Hoặc bắt request khi Thunderbird bắt đầu OAuth

Ví dụ request sẽ có dạng: `https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

Client ID không phải bí mật. Client ID mặc định:

```text
9e5f94bc-e8a4-4e73-b8be-63364c29d753
```

Project cũng vẫn giữ demo IMAP/SMTP XOAUTH2 cũ để đọc hoặc gửi mail qua `outlook.office365.com` và `smtp.office365.com`.

Nếu ý bạn là kiểm tra xem một ứng dụng (ví dụ Thunderbird) đã được user consent hay chưa, với tài khoản Outlook cá nhân (@outlook.com, @hotmail.com, @live.com) bạn có thể kiểm tra các ứng dụng đã kết nối tại: `https://account.live.com/consent/Manage` Hoặc: `https://account.microsoft.com/privacy`

## Mục tiêu chính

- Lấy `refresh_token` cho tài khoản Outlook/Microsoft 365.
- Lưu token vào file trong thư mục project.
- Tái sử dụng `refresh_token` để lấy `access_token` mới.
- Đọc danh sách email mới nhất bằng Microsoft Graph API.
- Hỗ trợ workflow manual khi đăng nhập trên Chrome Android, ví dụ điện thoại Samsung đang kết nối ADB với Windows.
- Không cần client secret khi dùng public client ID Thunderbird.

## Cấu trúc file

| File | Vai trò |
| --- | --- |
| `config.py` | Cấu hình client ID, client secret nếu có, scopes và tên file lưu token. |
| `auth_client.py` | Tạo MSAL client. Nếu `ClientSecret` rỗng thì dùng public client. Nếu có secret thì dùng confidential client. |
| `get_token.py` | Chạy OAuth authorization code flow để lấy refresh token và access token lần đầu. |
| `refresh_token.py` | Dùng refresh token đã lưu để lấy access token mới. |
| `graph_demo.py` | Dùng Graph API để đọc email Outlook mới nhất. |
| `demo.py` | Demo IMAP/SMTP XOAUTH2 cũ, dùng token IMAP/SMTP để đọc inbox hoặc gửi email. |
| `api_main.py` | FastAPI app, cung cấp API lấy OAuth link và đổi authorization code lấy refresh token. |
| `api_schemas.py` | Định nghĩa JSON request/response cho API. |
| `oauth_session_store.py` | Lưu `oauth_session` tạm thời trong memory khi chạy API. |
| `oauth_utils.py` | Helper tạo random session/state và parse redirect URL để lấy `code`, `state`. |
| `requirements.txt` | Danh sách thư viện Python cần cài. |
| `server.cert`, `server.key` | Certificate tự ký cho local HTTPS callback `https://localhost:7598/`. |
| `.gitignore` | Bỏ qua virtualenv và các file token nhạy cảm. |

## Token files

Project có 2 nhóm token riêng:

| Profile | Refresh token file | Access token file | Dùng cho |
| --- | --- | --- | --- |
| `graph` | `graph_refresh_token` | `graph_access_token` | Microsoft Graph API. |
| `imap_smtp` | `imap_smtp_refresh_token` | `imap_smtp_access_token` | IMAP/SMTP XOAUTH2. |

Các file token này là bí mật. Không gửi cho người khác, không paste vào chat, không commit lên git.

## Logic OAuth đang triển khai

### 1. `config.py`

File này đang cấu hình:

```python
ClientId = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"
ClientSecret = ""
```

Vì `ClientSecret` rỗng, project dùng public client flow, phù hợp với client ID Thunderbird.

Scopes cho Graph API:

```python
GraphScopes = [
    "https://graph.microsoft.com/User.Read",
    "https://graph.microsoft.com/Mail.Read",
]
```

Không khai báo thủ công `offline_access` trong `GraphScopes` vì MSAL coi `offline_access`, `openid`, `profile` là reserved scopes và tự thêm vào URL OAuth khi cần.

Scopes cho IMAP/SMTP:

```python
ImapSmtpScopes = [
    "https://outlook.office.com/IMAP.AccessAsUser.All",
    "https://outlook.office.com/SMTP.Send",
]
```

### 2. `auth_client.py`

File này có 2 nhiệm vụ:

- `create_app()` tạo MSAL application.
- `get_token_config(profile)` chọn đúng scopes và tên file token theo profile.

Nếu `ClientSecret` có giá trị:

```text
ConfidentialClientApplication
```

Nếu `ClientSecret` rỗng:

```text
PublicClientApplication
```

Với workflow hiện tại dùng Thunderbird public client ID, project sẽ dùng `PublicClientApplication`.

### 3. `get_token.py`

File này dùng để lấy token lần đầu.

Luồng mặc định:

```text
CLI in OAuth URL -> bạn mở URL trong browser -> Microsoft login -> redirect về https://localhost:7598/ -> script nhận code -> đổi code thành token -> ghi file token
```

Luồng manual mode:

```text
CLI in OAuth URL -> bạn mở URL ở browser bất kỳ -> Microsoft login -> browser redirect về localhost và có thể báo lỗi -> bạn copy URL cuối có code=... -> paste vào terminal -> script đổi code thành token -> ghi file token
```

Manual mode đặc biệt phù hợp khi bạn mở link OAuth trên Chrome Android, vì `localhost` trên Android là điện thoại Android, không phải Windows.

### 4. `refresh_token.py`

File này dùng refresh token đã lưu để lấy access token mới.

Ví dụ với Graph:

```powershell
.\.venv\Scripts\python.exe refresh_token.py graph
```

Script sẽ:

- Đọc `graph_refresh_token`.
- Gọi Microsoft token endpoint qua MSAL.
- Ghi refresh token mới nếu Microsoft trả về refresh token mới.
- Ghi access token mới vào `graph_access_token`.
- In access token ra terminal.

### 5. `graph_demo.py`

File này đọc email qua endpoint:

```text
https://graph.microsoft.com/v1.0/me/messages
```

Mỗi lần chạy, script sẽ:

- Đọc `graph_refresh_token`.
- Lấy `access_token` mới qua MSAL.
- Gọi Microsoft Graph API.
- Lấy các trường: `receivedDateTime`, `from`, `subject`, `bodyPreview`, `webLink`.
- In email mới nhất ra terminal.

Tham số số lượng email:

```powershell
.\.venv\Scripts\python.exe graph_demo.py 5
```

Số `5` nghĩa là lấy 5 email mới nhất. Nếu không truyền số, mặc định lấy 15 email.

## Cài đặt trên Windows PowerShell

Mở PowerShell tại thư mục project:

```powershell
cd E:\2WEBApp\M365-IMAP
```

Kiểm tra Python:

```powershell
python --version
```

Tạo virtualenv:

```powershell
python -m venv .venv
```

Cài dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Kiểm tra thư viện đã cài:

```powershell
.\.venv\Scripts\python.exe -m pip list
```

Kiểm tra cú pháp các script:

```powershell
.\.venv\Scripts\python.exe -m py_compile auth_client.py config.py get_token.py refresh_token.py graph_demo.py demo.py api_main.py api_schemas.py oauth_session_store.py oauth_utils.py
```

## Chạy API OAuth Outlook

Ngoài các script CLI terminal, project có thêm FastAPI service để lấy OAuth link và đổi authorization code thành refresh token qua HTTP API.

Chạy API local:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api_main:app --host 127.0.0.1 --port 8000
```

API mặc định chạy tại:

```text
http://127.0.0.1:8000
```

Kiểm tra API đang chạy:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Response:

```json
{"status":"ok"}
```

### API 1: lấy link OAuth Outlook

Endpoint:

```http
POST http://127.0.0.1:8000/api/outlook/oauth/link
```

PowerShell:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/outlook/oauth/link
```

Response JSON mẫu:

```json
{
  "oauth_session": "KXnQdLr4...",
  "state": "qk1bU27D...",
  "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=...",
  "expires_in": 600
}
```

Ý nghĩa:

- `auth_url`: link Microsoft OAuth. Bạn copy link này và tự mở bằng Chrome, Edge, GPM Browser hoặc browser tùy ý.
- `oauth_session`: session tạm thời của API. Cần giữ lại để gọi API thứ 2.
- `state`: giá trị chống giả mạo OAuth. API tự lưu và kiểm tra lại khi đổi token.
- `expires_in`: thời gian `oauth_session` còn hiệu lực, mặc định 600 giây.

Sau khi mở `auth_url` và login Microsoft thành công, browser sẽ redirect về URL dạng:

```text
https://localhost:7598/?code=...&state=...
```

Trang có thể báo lỗi certificate hoặc không kết nối được `localhost`. Điều này vẫn bình thường nếu bạn chỉ cần lấy URL trên thanh địa chỉ. Hãy copy nguyên URL cuối cùng có `code=...` và `state=...`.

### API 2: đổi redirect URL lấy refresh token

Endpoint:

```http
POST http://127.0.0.1:8000/api/outlook/oauth/refresh-token
```

Request JSON, cách khuyến nghị là gửi nguyên redirect URL:

```json
{
  "oauth_session": "KXnQdLr4...",
  "redirect_url": "https://localhost:7598/?code=...&state=..."
}
```

PowerShell:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/outlook/oauth/refresh-token `
  -H "Content-Type: application/json" `
  -d '{"oauth_session":"PASTE_OAUTH_SESSION","redirect_url":"PASTE_FULL_REDIRECT_URL"}'
```

Nếu bạn dùng Git Bash:

```bash
curl -X POST http://127.0.0.1:8000/api/outlook/oauth/refresh-token \
  -H "Content-Type: application/json" \
  -d '{"oauth_session":"PASTE_OAUTH_SESSION","redirect_url":"PASTE_FULL_REDIRECT_URL"}'
```

Response JSON mẫu khi thành công:

```json
{
  "refresh_token": "...",
  "access_token": "...",
  "expires_in": 3599,
  "scope": "https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/User.Read",
  "token_type": "Bearer"
}
```

Bạn lưu `refresh_token` này để dùng cho các API Microsoft Graph theo mục đích của bạn.

API cũng hỗ trợ gửi `code` và `state` đã parse sẵn thay vì gửi nguyên `redirect_url`:

```json
{
  "oauth_session": "KXnQdLr4...",
  "code": "authorization-code",
  "state": "qk1bU27D..."
}
```

Lưu ý:

- `oauth_session` chỉ lưu trong memory của process API đang chạy.
- `oauth_session` hết hạn sau 600 giây.
- Sau khi đổi token thành công, `oauth_session` sẽ bị xóa và không dùng lại được.
- API không ghi refresh token ra file. API chỉ trả JSON để bạn tự lưu theo nhu cầu.
- Không chia sẻ `refresh_token`, `access_token`, `code` hoặc redirect URL có `code=...` cho người khác.

### Luồng test API nhanh

1. Chạy API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api_main:app --host 127.0.0.1 --port 8000
```

2. Mở terminal khác, lấy OAuth link:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/outlook/oauth/link
```

3. Copy `auth_url` trong response và mở bằng browser bạn muốn.
4. Login Microsoft.
5. Copy URL cuối trên thanh địa chỉ có `code=...&state=...`.
6. Gọi API đổi token bằng `oauth_session` ở bước 2 và `redirect_url` ở bước 5.
7. Lưu `refresh_token` trong response.

## Cách 1: Lấy Graph refresh token bằng manual mode, khuyến nghị cho Android Chrome

Đây là cách nên dùng nếu bạn muốn tạo tài khoản/login Microsoft trên Chrome Android rồi lấy token về project Windows.

Chạy lệnh:

```powershell
.\.venv\Scripts\python.exe get_token.py graph --manual
```

Terminal sẽ in ra OAuth URL dạng:

```text
https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=...
```

Làm tiếp như sau:

1. Copy toàn bộ URL từ terminal.
2. Mở Chrome Android trên điện thoại.
3. Paste URL vào thanh địa chỉ Chrome Android.
4. Đăng nhập Microsoft/Outlook thành công.
5. Sau khi login, Chrome Android sẽ redirect về:

```text
https://localhost:7598/?code=...
```

6. Vì đây là `localhost` của Android, trang có thể báo certificate error hoặc connection error. Điều này bình thường trong manual mode.
7. Copy toàn bộ URL trên thanh địa chỉ Chrome Android.
8. Quay lại PowerShell Windows.
9. Paste URL đó vào dòng hỏi:

```text
Paste final redirect URL or code:
```

Nếu thành công, terminal sẽ in:

```text
Refresh token acquired, writing to file graph_refresh_token
Access token acquired, writing to file graph_access_token
```

Sau bước này, project đã có refresh token Graph để đọc email.

## Cách 2: Lấy Graph refresh token bằng local callback trên Windows

Cách này phù hợp khi bạn mở OAuth URL bằng browser trên chính máy Windows.

Chạy:

```powershell
.\.venv\Scripts\python.exe get_token.py graph
```

Terminal sẽ in OAuth URL. Copy URL đó và mở bằng browser Windows.

Sau khi login, browser redirect về:

```text
https://localhost:7598/
```

Script Python trên Windows đang nghe port `7598`, nên nó sẽ tự nhận authorization code và tạo:

```text
graph_refresh_token
graph_access_token
```

Nếu browser báo cảnh báo certificate do `server.cert` là self-signed certificate, bạn có thể dùng manual mode ở phần trên.

## Cách 3: Android Chrome với ADB reverse, tùy chọn

Nếu bạn muốn Android Chrome redirect trực tiếp về server Python trên Windows mà không copy URL cuối thủ công, có thể thử ADB reverse.

Điện thoại Android cần đang kết nối ADB với Windows.

Kiểm tra thiết bị:

```powershell
adb devices
```

Tạo reverse port:

```powershell
adb reverse tcp:7598 tcp:7598
```

Chạy OAuth callback mode:

```powershell
.\.venv\Scripts\python.exe get_token.py graph
```

Copy OAuth URL từ terminal, mở bằng Chrome Android và đăng nhập.

Nếu ADB reverse hoạt động, request từ Android:

```text
https://localhost:7598/
```

sẽ được chuyển về Windows port `7598`, và script sẽ tự tạo token files.

Nếu gặp lỗi certificate hoặc không redirect được, quay lại manual mode:

```powershell
.\.venv\Scripts\python.exe get_token.py graph --manual
```

## Đọc email Outlook qua Microsoft Graph API

Sau khi đã có `graph_refresh_token`, chạy:

```powershell
.\.venv\Scripts\python.exe graph_demo.py
```

Mặc định lấy 15 email mới nhất.

Lấy 5 email mới nhất:

```powershell
.\.venv\Scripts\python.exe graph_demo.py 5
```

Lấy 20 email mới nhất:

```powershell
.\.venv\Scripts\python.exe graph_demo.py 20
```

Kết quả sẽ gồm các thông tin:

```text
Date
From
Subject
Preview
Link
```

`Link` là link mở email trong Outlook web.

## Refresh Graph access token thủ công

Nếu chỉ muốn refresh access token mà không đọc mail:

```powershell
.\.venv\Scripts\python.exe refresh_token.py graph
```

Script sẽ đọc:

```text
graph_refresh_token
```

và ghi:

```text
graph_access_token
```

Access token cũng được in ra terminal. Không chia sẻ access token này.

## Xóa token để login lại tài khoản khác

Nếu muốn đổi tài khoản Outlook/Microsoft, xóa token cũ trước.

PowerShell:

```powershell
Remove-Item .\graph_refresh_token -ErrorAction SilentlyContinue
Remove-Item .\graph_access_token -ErrorAction SilentlyContinue
```

Sau đó chạy lại:

```powershell
.\.venv\Scripts\python.exe get_token.py graph --manual
```

## IMAP/SMTP profile cũ

Nếu bạn muốn dùng IMAP/SMTP XOAUTH2 thay vì Graph API, dùng profile `imap_smtp`.

Lấy token IMAP/SMTP bằng callback mode:

```powershell
.\.venv\Scripts\python.exe get_token.py imap_smtp
```

Lấy token IMAP/SMTP bằng manual mode:

```powershell
.\.venv\Scripts\python.exe get_token.py imap_smtp --manual
```

Refresh token IMAP/SMTP:

```powershell
.\.venv\Scripts\python.exe refresh_token.py imap_smtp
```

Chạy demo IMAP/SMTP:

```powershell
.\.venv\Scripts\python.exe demo.py
```

Demo sẽ hỏi email và lựa chọn:

```text
inbox
message
```

- `inbox`: đọc email từ INBOX bằng IMAP XOAUTH2.
- `message`: gửi email bằng SMTP XOAUTH2.

Lưu ý: với một số tài khoản Outlook cá nhân, Graph API thường dễ dùng hơn IMAP/SMTP. IMAP/SMTP có thể phụ thuộc cấu hình tenant hoặc chính sách tài khoản.

## Các lệnh thường dùng

### Cài lại dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Kiểm tra project compile được

```powershell
.\.venv\Scripts\python.exe -m py_compile auth_client.py config.py get_token.py refresh_token.py graph_demo.py demo.py api_main.py api_schemas.py oauth_session_store.py oauth_utils.py
```

### Lấy Graph token bằng manual mode

```powershell
.\.venv\Scripts\python.exe get_token.py graph --manual
```

### Đọc 5 email mới nhất

```powershell
.\.venv\Scripts\python.exe graph_demo.py 5
```

### Refresh Graph access token

```powershell
.\.venv\Scripts\python.exe refresh_token.py graph
```

### Kiểm tra ADB device

```powershell
adb devices
```

### Bật ADB reverse cho port 7598

```powershell
adb reverse tcp:7598 tcp:7598
```

### Xem trạng thái git

```powershell
git status --short
```

## Troubleshooting

### Lỗi `Refresh token file graph_refresh_token not found`

Bạn chưa lấy Graph refresh token lần đầu.

Chạy:

```powershell
.\.venv\Scripts\python.exe get_token.py graph --manual
```

### Lỗi `You cannot use any scope value that is reserved`

Không thêm thủ công `offline_access`, `openid`, `profile` vào scopes trong `config.py`. MSAL tự thêm các scope reserved này.

### Android mở `https://localhost:7598/` nhưng không vào được

Đây là bình thường nếu dùng Android Chrome mà không dùng ADB reverse. `localhost` trên Android là điện thoại, không phải Windows.

Cách xử lý khuyến nghị:

```powershell
.\.venv\Scripts\python.exe get_token.py graph --manual
```

Sau đó copy URL cuối có `code=...` từ Chrome Android và paste vào terminal Windows.

### Browser báo certificate error

Project dùng `server.cert` và `server.key` self-signed cho local HTTPS callback. Nếu browser chặn certificate, dùng manual mode:

```powershell
.\.venv\Scripts\python.exe get_token.py graph --manual
```

### Graph API trả lỗi 401 hoặc token invalid

Thử refresh token:

```powershell
.\.venv\Scripts\python.exe refresh_token.py graph
```

Nếu vẫn lỗi, xóa token và login lại:

```powershell
Remove-Item .\graph_refresh_token -ErrorAction SilentlyContinue
Remove-Item .\graph_access_token -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe get_token.py graph --manual
```

### Graph API trả lỗi permission hoặc consent

Tài khoản hoặc tenant có thể chưa cho phép app Thunderbird truy cập `Mail.Read`. Với tenant công ty, admin có thể cần consent app trước.

### Không nên paste authorization code hoặc token vào chat

Authorization code trong URL `code=...` thường dùng một lần, nhưng vẫn không nên chia sẻ. Refresh token và access token là bí mật nghiêm trọng hơn. Nếu đã lộ refresh token, nên revoke app access trong Microsoft account/Azure và tạo token mới.

## Bảo mật

- `graph_refresh_token` có thể dùng để lấy access token mới và đọc email theo quyền đã consent.
- `graph_access_token` là token ngắn hạn nhưng vẫn có thể đọc mail trong thời gian còn hiệu lực.
- Không commit token lên git.
- Không gửi token qua chat, log, email hoặc ticket.
- Nếu token bị lộ, revoke quyền app trong Microsoft account hoặc Azure Portal rồi tạo lại token.
- Chỉ dùng project này với tài khoản bạn sở hữu hoặc có quyền kiểm thử hợp lệ.

## Ghi chú về Thunderbird public client ID

Project dùng public client ID của Thunderbird để mô phỏng OAuth public client flow. Vì đây là public client, không có client secret.

Điều này phù hợp cho công cụ desktop/script cá nhân, nhưng quyền truy cập vẫn phụ thuộc vào consent của Microsoft account hoặc tenant.

## Workflow khuyến nghị hiện tại

Nếu bạn tạo/login tài khoản Outlook trên Chrome Android và muốn lấy refresh token về Windows project, dùng workflow này:

```powershell
cd E:\2WEBApp\M365-IMAP
.\.venv\Scripts\python.exe get_token.py graph --manual
```

Sau đó:

1. Copy OAuth URL từ terminal.
2. Paste vào Chrome Android.
3. Login Microsoft.
4. Copy URL cuối có `code=...` từ thanh địa chỉ Chrome Android.
5. Paste vào terminal Windows.
6. Chờ script ghi `graph_refresh_token`.
7. Đọc email:

```powershell
.\.venv\Scripts\python.exe graph_demo.py 5
```
