# Eye HCI · Iris Studio

Điều khiển máy tính bằng mắt từ webcam, với giao diện liquid glass và đôi mắt 3D phản hồi trực tiếp. Python xử lý MediaPipe và lệnh hệ điều hành; trình duyệt hiển thị giao diện qua localhost. Không cần dịch vụ cloud hoặc CDN khi chạy.

## Cài đặt và chạy

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p models
curl -L -o models/face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
python step6_hci.py
```

Trình duyệt tự mở tại http://127.0.0.1:8765. Mặc định mô phỏng lệnh, camera chưa bật.

```sh
python step6_hci.py --camera 1 --port 8766
python step6_hci.py --no-browser
python step6_hci.py --real
```

`--real` chọn chế độ điều khiển thật từ đầu; vẫn cần bật camera và nhấn Tiếp tục. macOS cần cấp quyền Camera cho ứng dụng chạy Python; Accessibility cần cho PyAutoGUI khi điều khiển thật.

## Sử dụng

1. Nhấn **Bật camera**, ngồi sao cho thấy rõ cả hai mắt.
2. Nhấn **Hiệu chuẩn**, làm theo 7 bước: giữa → trái → phải → lên → xuống → mở mắt → nhắm cả hai mắt. Giữ đầu thẳng, chỉ di chuyển mắt. Mỗi bước khoảng 2,8 giây; tiếng báo đánh dấu chuyển bước và kết thúc. Bước mất dấu mặt hoặc mẫu thiếu ổn định được thu lại.
3. Khi hoàn tất, hồ sơ được lưu tại `profiles/default.json`. Nhấn **Tiếp tục**, nhìn thẳng với mắt mở để sẵn sàng.
4. Mặc định xem lệnh trong **Nhịp tương tác**. Bật **Điều khiển thật** khi muốn phát phím/cuộn/click; đổi chế độ luôn tạm dừng và cần nhấn Tiếp tục.
5. Dùng **Tạm dừng** hoặc Esc khi trang đang được focus; **Dừng camera** giải phóng camera. Ctrl+C trong Terminal để thoát máy chủ.

Hồ sơ tự tải ở lần chạy sau. Hiệu chuẩn lại khi đổi người dùng, vị trí camera hoặc tư thế ngồi. Bản hiện tại lưu một hồ sơ mặc định.

| Cử chỉ | Lệnh |
| --- | --- |
| Giữ liếc phải ít nhất 0,40 giây | Phím phải / NEXT |
| Giữ liếc trái ít nhất 0,40 giây | Phím trái / PREV |
| Giữ liếc lên / xuống ít nhất 0,40 giây | Cuộn +3 / −3 |
| Nhắm cả hai mắt 0,23–0,50 giây rồi mở | Click tại vị trí con trỏ hiện tại |

Sau một lệnh hướng, nhìn về giữa để kích hoạt lần tiếp theo. Cooldown giữa các lệnh là 0,50 giây. Chớp mắt tự nhiên quá ngắn hoặc nhắm quá lâu không tạo click. Đôi mắt 3D phản ánh độ mở từng mắt, kể cả nháy một mắt; nháy một mắt không phát click.

Lệnh thật tác động vào ứng dụng đang có focus. Đôi mắt 3D thể hiện hướng tương đối; phần mềm chưa ánh xạ ánh nhìn thành vị trí con trỏ trên màn hình. Esc trong giao diện không phải phím nóng toàn hệ thống. PyAutoGUI vẫn bật failsafe ở góc màn hình.

## Kiến trúc và kiểm thử

- `eye_hci/core.py`: hiệu chuẩn, hồ sơ, máy trạng thái và nhận diện thao tác; không phụ thuộc camera.
- `eye_hci/runtime.py`: camera/MediaPipe, làm mượt theo thời gian, lưu hồ sơ và phát lệnh.
- `step6_hci.py`: máy chủ HTTP chỉ bind 127.0.0.1 và CLI.
- `web/`: giao diện HTML/CSS/JS, mắt 3D WebGL chạy offline.
- `tests/`: kiểm thử dữ liệu mô phỏng và API local.
- `BAO_CAO_CAI_TIEN.md`: mô tả thay đổi, cách làm và giới hạn kiểm chứng.

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Các file `step1_camera_test.py`, `step2_landmarks.py`, `step3_blink.py` tiếp tục dùng cho chẩn đoán riêng. Thuật toán vẫn dựa trên luật và hiệu chuẩn, chưa huấn luyện mô hình gaze, chưa bù quay đầu. Chất lượng thực tế cần đánh giá với người dùng và camera của bạn.

## Giao diện sáng / tối

Dùng bộ chọn **☀ Sáng / ☾ Tối / ◐ Hệ thống** ở góc trên bên phải. Trình duyệt tự nhớ lựa chọn; lần đầu mặc định Tối. Chế độ Hệ thống tự theo giao diện hệ điều hành. Các panel sử dụng lớp kính trong, viền phản sáng và nền màu để hiệu ứng liquid glass rõ hơn.

## Hình nền desktop và cửa sổ nổi (macOS)

Chọn **Hệ thống** trong bản desktop để bật kính nhìn xuyên thật: macOS làm mờ nội dung của cửa sổ/ứng dụng nằm ngay phía sau Iris Studio. Khi kéo cửa sổ nổi qua Google Docs hoặc ứng dụng khác, lớp kính tự lấy nội dung bên dưới để phối nền. Không chụp, lưu hoặc gửi ảnh của ứng dụng phía sau; không cần cấp quyền Screen Recording cho hiệu ứng này. Màu chữ theo sáng/tối của macOS. Trong trình duyệt thông thường, Hệ thống chỉ dùng ảnh wallpaper được làm mờ 20 px làm phương án dự phòng. Nếu macOS bật Reduce Transparency, hệ thống có thể giảm hiệu ứng nhìn xuyên.

Để thu gọn và kéo đè trên ứng dụng khác, nhấp đúp **Iris Studio.command** trong Finder hoặc chạy:

```sh
.venv/bin/python step6_hci.py --desktop
```

- **Thu gọn**: cửa sổ nhỏ luôn nổi, giữ đôi mắt 3D và các nút điều khiển chính.
- Kéo **thanh tiêu đề** để di chuyển; có thể đổi kích thước bằng cạnh cửa sổ.
- **Mở rộng**: trở lại kích thước trước đó, bỏ chế độ luôn nổi.
- **—**: thu xuống Dock; nhấp biểu tượng ứng dụng trong Dock để mở lại.
- Để hiệu chuẩn, mở rộng cửa sổ trước. Camera và điều khiển không bị tắt chỉ vì thu gọn hoặc thu xuống Dock; dùng Tạm dừng khi cần.

macOS dùng cửa sổ AppKit/WKWebView riêng. Lần chạy đầu biên dịch shell Objective-C từ `native/IrisStudio.m` bằng Command Line Tools đã có trên máy; kết quả ở `build/Iris Studio.app`. Khi đóng cửa sổ desktop, máy chủ và camera của phiên đó cũng dừng. File `.command` dùng cổng 8765 ổn định để giữ lựa chọn giao diện. Nếu đã có dashboard trên cổng này, bản desktop kết nối vào cùng phiên để dùng chung camera; đóng cửa sổ trong trường hợp này không tắt máy chủ có sẵn.

Trình duyệt thông thường chỉ có thể xem dashboard; nút Thu gọn sẽ hiển thị hướng dẫn mở bản desktop vì trình duyệt không có quyền đặt cửa sổ luôn nổi.
