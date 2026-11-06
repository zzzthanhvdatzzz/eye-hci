# Báo cáo cải tiến Eye HCI · Iris Studio

Ngày: 05/11/2026

## 1. Phạm vi và kết quả

Đã triển khai ba nhóm cải tiến: chặn lệnh khi chưa sẵn sàng/mất mặt; đo thao tác theo thời gian; hiệu chuẩn có hướng dẫn và lưu hồ sơ. Đồng thời thay cửa sổ OpenCV của `step6_hci.py` bằng dashboard localhost phong cách liquid glass, có camera và đôi mắt 3D phản hồi theo tín hiệu mắt.

Không thay đổi mô hình FaceLandmarker có sẵn; thuật toán nhận dạng cử chỉ vẫn là rule-based. Các script bước 1–3 được giữ để chẩn đoán.

## 2. Trạng thái và ngăn lệnh ngoài ý muốn

### Trước cải tiến

- Tâm hiệu chuẩn khởi tạo bằng 0; xử lý lệnh đã chạy trước frame 45.
- Không thấy mặt thì bỏ qua khối xử lý nhưng giữ biến đếm chớp mắt/giữ hướng.
- Không có thao tác tạm dừng trong phiên ngoài việc thoát cửa sổ.

### Cách triển khai

`Controller` trong `eye_hci/core.py` chỉ cho phát lệnh khi đã có hồ sơ hợp lệ và không tạm dừng. `Runtime` quản lý trạng thái hiển thị STOPPED, STARTING, CALIBRATING, PAUSED, ACTIVE, NO_FACE và ERROR.

- Khởi động, tải hồ sơ, hoàn tất hiệu chuẩn và đổi chế độ thật/mô phỏng đều đưa hệ thống về tạm dừng.
- API từ chối Tiếp tục nếu thiếu camera, khuôn mặt hoặc hồ sơ, hoặc đang hiệu chuẩn.
- Mất mặt xóa thời điểm bắt đầu giữ hướng, thời điểm nhắm mắt, tiến độ và trạng thái armed.
- Khi nhìn thấy mặt trở lại, cần nhìn thẳng với mắt mở để armed lại. Nếu trước đó đang ACTIVE, hệ thống tiếp tục theo quy tắc này; phiên PAUSED vẫn cần Tiếp tục.
- Khoảng cách giữa hai mẫu lớn hơn 250 ms cũng hủy thao tác đang chờ, tránh hoàn tất một cử chỉ qua thời gian camera bị khựng.
- Khi mắt đóng hoặc chỉ một mắt dưới ngưỡng, không tích lũy lệnh hướng.
- Lỗi camera/model/phát lệnh đưa hệ thống về ERROR, ngừng điều khiển và giải phóng tài nguyên trong `finally`.

Nút Tạm dừng và Esc khi trang đang focus cho phép dừng nhận lệnh. Nút Dừng camera tắt nhận lệnh ngay và yêu cầu worker giải phóng camera sau lần đọc hiện tại.

## 3. Từ đếm frame sang đo thời gian

### Trước cải tiến

Giữ hướng 12 frame và nhắm mắt 7–15 frame khiến thời gian thao tác thay đổi theo FPS. Điều kiện `hn == DW` chỉ có một cơ hội kiểm tra; nếu đúng lúc cooldown còn hiệu lực, lệnh có thể bị bỏ qua.

### Cách triển khai

Mọi phép đo cử chỉ sử dụng `time.monotonic()` và các mốc thời gian:

| Tham số | Giá trị mặc định | Ý nghĩa |
| --- | --- | --- |
| DWELL | 0,40 giây | Thời gian giữ hướng tối thiểu |
| BLINK_MIN | 0,23 giây | Thời gian nhắm cả hai mắt tối thiểu |
| BLINK_MAX | 0,50 giây | Thời gian nhắm cả hai mắt tối đa |
| COOLDOWN | 0,50 giây | Khoảng cách tối thiểu giữa hai lệnh |

Khi giữ hướng, điều kiện là thời gian đã trôi qua **lớn hơn hoặc bằng** DWELL và cooldown đã hết. Điều kiện được xét ở mỗi mẫu mới; không phụ thuộc một frame duy nhất. Sau khi phát một lệnh hướng, cần trở về trung tâm để nhận lệnh tiếp.

Blink được xác nhận khi mở mắt lại, dựa trên thời lượng nhắm cả hai mắt. Các thao tác ngoài khoảng quy định không tạo SELECT. Lệnh SELECT là click tại con trỏ hiện có, không phải click theo tọa độ ánh nhìn.

Bộ lọc gaze sử dụng hệ số `alpha = 1 - exp(-dt / 0.08)` thay cho hệ số cố định mỗi frame. Nhờ vậy tốc độ đáp ứng của bộ lọc ít phụ thuộc FPS hơn. Tọa độ landmark giữ kiểu float trong tính toán. Tốc độ lấy mẫu vẫn quyết định độ phân giải thời gian thực tế, nên kết quả tại 15 FPS có sai số lấy mẫu lớn hơn 60 FPS.

## 4. Hiệu chuẩn cá nhân và lưu hồ sơ

### Trước cải tiến

Lấy một giá trị đã làm mượt tại frame 45 làm tâm; ngưỡng hướng và EAR được viết cố định trong mã.

### Cách triển khai

`Calibration` thu dữ liệu theo 7 bước tự chuyển: nhìn giữa, trái, phải, lên, xuống, mở mắt tự nhiên, nhắm cả hai mắt. Mỗi bước có 1,3 giây chuẩn bị và 1,5 giây thu mẫu.

- Dùng mẫu float chưa làm mượt để không bị lẫn lịch sử bước trước.
- Lấy trung vị tọa độ và EAR từ nhiều mẫu; yêu cầu ít nhất 8 mẫu.
- Kiểm tra độ dao động bằng median absolute deviation: quá 0,035 cho tọa độ hoặc 0,04 cho EAR thì thu lại bước đó. Bước nhắm mắt chỉ xét ổn định EAR vì iris lúc này thiếu tin cậy.
- Mất mặt xóa mẫu và thời gian của bước hiện tại.
- Tính biên trái/phải/lên/xuống so với tâm riêng biệt. Biên phải đạt tối thiểu 0,008; ngưỡng kích hoạt bằng 50% biên đo được.
- Tính ngưỡng EAR riêng cho từng mắt bằng trung điểm giữa EAR mở và nhắm. Chênh lệch mở–nhắm phải đạt ít nhất 0,04 ở cả hai mắt.
- Nếu chưa tách được các hướng hoặc trạng thái mắt, báo hiệu chuẩn thất bại, không ghi đè hồ sơ cũ.
- Hồ sơ được kiểm tra giá trị hữu hạn, phiên bản và thứ tự ngưỡng trước khi dùng. Ghi qua file tạm rồi replace vào `profiles/default.json`.
- Hồ sơ được tự tải khi chạy lại nhưng cần người dùng nhấn Tiếp tục. Thư mục profiles được đưa vào `.gitignore`.

Bản này có một hồ sơ mặc định, chưa có trình quản lý nhiều người dùng. Các tỷ lệ 50% và ngưỡng chất lượng là mặc định ban đầu; cần đánh giá với người dùng thật trước khi tối ưu thêm.

## 5. Giao diện và đôi mắt 3D

Giao diện trong `web/` dùng nền gradient xanh ngọc, các panel trong suốt, backdrop blur, viền sáng và bóng mềm theo phong cách liquid glass. Bố cục hai cột trên desktop, một cột trên khung hẹp.

Các thành phần gồm camera trực tiếp, trạng thái phiên, hồ sơ, FPS, đôi mắt 3D, độ mở từng mắt, hướng nhìn, tiến độ giữ hướng, hiệu chuẩn 7 bước, nhật ký 12 lệnh gần nhất, công tắc thật/mô phỏng và các nút điều khiển.

Đôi mắt được dựng bằng WebGL fragment shader: tính giao tia với hai hình cầu 3D; đổ sáng, vẽ mống mắt/đồng tử, phản quang và mô phỏng mí mắt. Vector gaze xoay vị trí mống mắt tương đối; EAR từng mắt điều khiển độ mở mí riêng. Vì thế nháy một mắt cũng có phản hồi hình ảnh, còn click vẫn yêu cầu cả hai mắt. Đây là mô phỏng hình học đơn giản, chưa phải mô hình giải phẫu mắt hoặc ước lượng góc nhìn tuyệt đối.

Trình duyệt lấy trạng thái và ảnh JPEG khoảng 10 lần/giây, render WebGL theo requestAnimationFrame và nội suy chuyển động. Độ trễ thực tế gồm camera, inference, polling và làm mượt, chưa được đo trên phiên người dùng thật. Có thông báo fallback nếu WebGL không khả dụng. Tiếng báo local giúp nhận biết bước nhắm mắt kết thúc.

## 6. Kiến trúc vận hành

- Python standard-library HTTP server chỉ lắng nghe `127.0.0.1`; không thêm framework backend.
- Worker duy nhất sở hữu camera và MediaPipe. Luồng HTTP nhận thao tác từ giao diện, dùng khóa để cập nhật trạng thái nhất quán.
- Ảnh chỉ được mã hóa và giữ trong RAM để hiển thị; không lưu video hoặc gửi tới cloud.
- Giao diện và shader không dùng CDN, font hoặc dịch vụ mạng ngoài.
- Yêu cầu điều khiển POST kiểm tra Host, Origin và header riêng để tránh trang khác phát lệnh trực tiếp; không bật CORS.
- Giữ chế độ mô phỏng mặc định và failsafe của PyAutoGUI.

## 7. Kiểm chứng

Đã chạy `.venv/bin/python -m unittest discover -s tests -v`: **17/17 ca đạt**.

Các nhóm kiểm thử:

1. Không phát lệnh khi thiếu hồ sơ hoặc đang tạm dừng.
2. Giữ hướng ở 15/30/60 FPS tạo một lệnh với thời gian tương đương trong sai số lấy mẫu.
3. Cooldown hết sau dwell vẫn phát lệnh.
4. Mất mặt giữa giữ hướng hoặc chớp mắt không nối tiếp cử chỉ cũ.
5. Sau gián đoạn cần về trung tâm trước khi nhận hướng mới.
6. Blink hợp lệ tạo SELECT; blink quá ngắn/quá dài không tạo SELECT.
7. Không nhận hướng khi nhắm mắt; khựng camera không hoàn tất dwell.
8. Hiệu chuẩn đủ 7 bước tạo đúng ngưỡng từ dữ liệu giả lập; mất mặt xóa mẫu hiện tại; biên quá nhỏ và hồ sơ NaN bị từ chối.
9. HTTP phục vụ giao diện/trạng thái; thiếu ảnh trả 204; chặn POST khác origin; chặn resume khi chưa sẵn sàng; pause/stop hoạt động.

Đã mở dashboard trong trình duyệt, kiểm tra bố cục khung hẹp và desktop, thấy đôi mắt WebGL hiển thị, và không thấy lỗi/warning console ở lần kiểm tra. Các dependency OpenCV và MediaPipe import thành công trong `.venv` sẵn có.

**Giới hạn kiểm chứng:** chưa thực hiện hiệu chuẩn bằng mắt người thật, chưa đo recall/false positives/độ trễ mới và chưa phát lệnh thật vào ứng dụng. Các ca mô phỏng chứng minh logic thời gian/trạng thái, không chứng minh độ chính xác thị giác. Chưa có head-pose compensation. Cần thử thực tế với ánh sáng, kính và camera của người dùng.

## 8. Quy trình nghiệm thu thực tế

1. Chạy `python step6_hci.py`, bật camera, hoàn tất hiệu chuẩn trong chế độ mô phỏng.
2. Thử 10 lần mỗi hướng và 10 lần nhắm/mở mắt chủ động; đối chiếu nhật ký lệnh.
3. Che camera giữa lúc giữ hướng rồi bỏ che; xác nhận không có lệnh cũ và phải nhìn giữa để kích hoạt lại.
4. Tạm dừng, thử các cử chỉ; xác nhận nhật ký không tăng.
5. Chạy lại để kiểm tra tải hồ sơ; đổi chỗ ngồi rồi hiệu chuẩn lại.
6. Bật điều khiển thật, nhấn Tiếp tục rồi chuyển focus sang ứng dụng dùng để thử phím/cuộn. Kiểm tra click tại vị trí con trỏ hiện tại.
7. Ghi số lệnh đúng, lệnh nhầm mỗi phút và độ trễ; điều chỉnh các hằng số trong core nếu cần.

## 9. Cập nhật giao diện sáng/tối

Bổ sung bộ chọn Sáng / Tối / Hệ thống ở góc trên bên phải. Lựa chọn được lưu trong localStorage của trình duyệt và áp dụng trước khi tải CSS để hạn chế nháy sai màu lúc mở trang. Lần đầu mặc định Tối; chế độ Hệ thống theo dõi thay đổi prefers-color-scheme trực tiếp.

Tăng độ trong của panel, thêm viền phản sáng, nền màu phía sau kính, backdrop blur và saturation; dùng biến CSS để đồng bộ chữ, nút và trạng thái ở cả hai chế độ. Hỗ trợ prefers-reduced-transparency bằng nền đặc nếu hệ thống yêu cầu giảm trong suốt.

Đã kiểm tra chuyển Sáng → Tối trong trình duyệt, tải lại vẫn giữ Tối, màu nền computed thay đổi đúng và không ghi nhận lỗi console. Ảnh minh họa: `docs/theme-dark.png`.

## 10. Hình nền hệ thống và cửa sổ desktop

Đổi ý nghĩa lựa chọn Hệ thống: gọi `/api/wallpaper`, đọc ảnh hình nền màn hình chính qua `NSWorkspace.desktopImageURLForScreen`, giải mã bằng AppKit và trả PNG trong RAM. CSS đặt ảnh làm background dưới các panel kính. Không chụp màn hình ứng dụng khác và không thay đổi wallpaper của hệ điều hành. Nếu ảnh không đọc được, dùng nền dự phòng. Với video/hình nền động, chỉ có thể hiển thị ảnh tĩnh khả dụng từ macOS. Màu chữ vẫn theo sáng/tối hệ thống.

Thêm `--desktop` và `Iris Studio.command`. Trên macOS, Python khởi chạy shell AppKit/WKWebView được biên dịch từ Objective-C tại máy bằng Xcode Command Line Tools. Shell có thanh tiêu đề native để kéo cửa sổ và bridge chỉ nhận lệnh từ localhost cùng cổng. Thu gọn đặt `NSWindow.level = floating`, bố cục mini và kích thước 420×570; Mở rộng khôi phục kích thước cũ và level bình thường; nút — gọi miniaturize xuống Dock. Chế độ nổi hỗ trợ các desktop thông thường và fullScreenAuxiliary; một số cửa sổ hệ thống có mức ưu tiên cao vẫn có thể nằm trên nó. Đóng app kết thúc máy chủ và camera của phiên desktop.

Bổ sung kiểm thử API ảnh nền thành công/thất bại và WindowAPI thu gọn/khôi phục/thu Dock với mock. Tổng **21 ca kiểm thử** đạt ở lần kiểm tra bổ sung. Đã đọc được PNG từ wallpaper thực và xác nhận trình duyệt hiển thị đúng background. Kiểm thử mock WindowAPI áp dụng adapter pywebview dự phòng, không thay thế kiểm tra tương tác shell Objective-C thực tế. Dependency `pywebview` là backend dự phòng cho nền tảng khác; macOS sử dụng shell Objective-C.

Tài liệu API tham khảo khi triển khai adapter: https://pywebview.flowrl.com/api/.


Kiểm tra tương tác thực tế bổ sung: đã mở app macOS qua LaunchServices, chọn Hệ thống và bấm Thu gọn; accessibility xác nhận nút đổi thành Mở rộng, ảnh chụp cửa sổ xác nhận bố cục mini 420 px với mắt 3D và nút điều khiển. Shell Objective-C đã biên dịch thành công bằng clang. Chưa kiểm tra riêng nút thu Dock và tình huống chồng lên mọi loại cửa sổ toàn màn hình. Trình khởi chạy tái sử dụng dashboard đang chạy tại cổng 8765 khi có để dùng chung camera và giữ origin lưu theme ổn định.


## 11. Kính nhìn xuyên ứng dụng phía sau

Thay nền wallpaper tĩnh của bản desktop bằng `NSVisualEffectView` với `NSVisualEffectBlendingModeBehindWindow`. Đây là lớp dưới WKWebView; cửa sổ đặt `opaque = NO`, background clear, WKWebView tắt drawsBackground và đặt underPageBackgroundColor clear. CSS html/body trong chế độ Hệ thống trở thành transparent; panel chỉ phủ lớp tint mỏng. Bridge native bật/tắt lớp kính khi chuyển Hệ thống hoặc Sáng/Tối, theo appearance của hệ điều hành.

WindowServer phối và làm mờ nội dung nằm sau cửa sổ theo vị trí thực, không gọi API chụp màn hình hay lưu nội dung của ứng dụng khác. Vì thế không cần chọn riêng Google Docs; kéo cửa sổ đến nơi cần dùng là đủ. Trình duyệt không có nền xuyên cửa sổ, nên vẫn có wallpaper fallback nhưng đã làm mờ 20 px bằng pseudo-element riêng, giữ chữ và nút sắc nét.

Đã biên dịch shell Objective-C thành công, chạy lại 21 kiểm thử đạt, khởi động app thực và xác nhận chế độ Hệ thống cùng bố cục thu gọn hoạt động. Ảnh cửa sổ riêng: `docs/live-glass.png`; ảnh chụp riêng cửa sổ có thể không bao gồm phần nền của ứng dụng khác do WindowServer tổng hợp. Chưa đo định lượng độ mờ hoặc kiểm tra riêng với Google Docs. macOS Reduce Transparency có thể thay kính bằng nền đặc.

Tham khảo chính thức: [Apple — behindWindow](https://developer.apple.com/documentation/appkit/nsvisualeffectview/blendingmode-swift.enum/behindwindow).
