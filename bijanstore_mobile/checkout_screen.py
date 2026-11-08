import flet as ft
import api_client
from state import AppState


class CheckoutScreen(ft.View):
    def __init__(self, page: ft.Page, on_success):
        self.page_ref = page
        self.on_success = on_success

        # فیلدهای فرم
        self.receiver_name = ft.TextField(label="نام گیرنده", rtl=True)
        self.receiver_phone = ft.TextField(label="شماره تماس", rtl=True, keyboard_type=ft.KeyboardType.PHONE)
        self.province = ft.TextField(label="استان", rtl=True)
        self.city = ft.TextField(label="شهر", rtl=True)
        self.postal_code = ft.TextField(label="کد پستی", rtl=True, keyboard_type=ft.KeyboardType.NUMBER)
        self.address = ft.TextField(label="آدرس کامل", rtl=True, multiline=True, min_lines=2)
        self.notes = ft.TextField(label="توضیحات (اختیاری)", rtl=True)
        self.coupon = ft.TextField(label="کد تخفیف (اختیاری)", rtl=True)
        self.error_text = ft.Text(color=ft.Colors.RED, size=13)

        super().__init__(
            route="/checkout",
            appbar=ft.AppBar(
                title=ft.Text("ثبت سفارش"),
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
                leading=ft.IconButton(
                    ft.Icons.ARROW_FORWARD,
                    on_click=lambda e: page.navigate("/cart"),
                ),
            ),
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("اطلاعات گیرنده", size=18, weight=ft.FontWeight.BOLD),
                            self.receiver_name,
                            self.receiver_phone,
                            ft.Divider(),
                            ft.Text("آدرس ارسال", size=18, weight=ft.FontWeight.BOLD),
                            self.province,
                            self.city,
                            self.postal_code,
                            self.address,
                            ft.Divider(),
                            self.notes,
                            self.coupon,
                            self.error_text,
                            ft.Button(
                                "ثبت نهایی سفارش",
                                icon=ft.Icons.CHECK,
                                width=350,
                                on_click=self.submit_order,
                            ),
                        ],
                        spacing=12,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    padding=20,
                    expand=True,
                )
            ],
        )

    def submit_order(self, e):
        self.error_text.value = ""

        # اعتبارسنجی ساده
        if not self.receiver_name.value.strip():
            self.error_text.value = "نام گیرنده الزامی است."
            self.page_ref.update()
            return

        if not self.receiver_phone.value.strip():
            self.error_text.value = "شماره تماس الزامی است."
            self.page_ref.update()
            return

        if not self.province.value.strip() or not self.city.value.strip():
            self.error_text.value = "استان و شهر الزامی است."
            self.page_ref.update()
            return

        if not self.address.value.strip():
            self.error_text.value = "آدرس کامل الزامی است."
            self.page_ref.update()
            return

        # داده‌ها برای API
        data = {
            "receiver_name": self.receiver_name.value.strip(),
            "receiver_phone": self.receiver_phone.value.strip(),
            "shipping_province": self.province.value.strip(),
            "shipping_city": self.city.value.strip(),
            "shipping_postal_code": self.postal_code.value.strip() or "0000000000",
            "shipping_address": self.address.value.strip(),
            "notes": self.notes.value.strip(),
            "coupon_code": self.coupon.value.strip(),
        }

        success, result = api_client.checkout(data)

        if success:
            # نمایش پیام موفقیت
            self.page_ref.snack_bar = ft.SnackBar(
                ft.Text(f"✅ {result.get('message', 'سفارش ثبت شد')}"),
                bgcolor=ft.Colors.GREEN,
            )
            self.page_ref.snack_bar.open = True

            # نمایش دیالوگ پرداخت
            self.show_payment_dialog(result.get("orders", []))
        else:
            error_msg = result.get("error", "خطا در ثبت سفارش")
            if isinstance(result, dict):
                # اگر خطا در فرمت فیلدها بود
                for k, v in result.items():
                    if isinstance(v, list):
                        error_msg = f"{k}: {v[0]}"
                        break
            self.error_text.value = str(error_msg)
            self.page_ref.update()

    def show_payment_dialog(self, orders):
        """نمایش دیالوگ پرداخت برای سفارش‌های ایجادشده"""
        if not orders:
            self.on_success()
            return

        order = orders[0]  # فعلاً اولین سفارش
        order_number = order["order_number"]

        def do_pay(e):
            dialog.open = False
            self.page_ref.update()

            # درخواست لینک پرداخت از API
            import requests
            from api_client import API_BASE, _headers

            try:
                r = requests.post(
                    f"{API_BASE}/orders/{order_number}/pay/",
                    headers=_headers(),
                )
                if r.status_code == 200:
                    payment_url = r.json().get("payment_url")
                    # باز کردن لینک در مرورگر
                    import webbrowser
                    webbrowser.open(payment_url)
                    self.page_ref.snack_bar = ft.SnackBar(
                        ft.Text("لطفاً پرداخت را در مرورگر تکمیل کنید.")
                    )
                    self.page_ref.snack_bar.open = True
                    self.page_ref.update()
                else:
                    self.page_ref.snack_bar = ft.SnackBar(
                        ft.Text(f"خطا: {r.text}"),
                        bgcolor=ft.Colors.RED,
                    )
                    self.page_ref.snack_bar.open = True
                    self.page_ref.update()
            except Exception as ex:
                print(f"خطا: {ex}")

        def close_and_go(e):
            dialog.open = False
            self.on_success()

        dialog = ft.AlertDialog(
            title=ft.Text("✅ سفارش ثبت شد"),
            content=ft.Column(
                [
                    ft.Text(f"شماره سفارش: {order_number}"),
                    ft.Text(f"مبلغ: {order['total']} تومان"),
                    ft.Text("برای تکمیل خرید، پرداخت را انجام دهید."),
                ],
                tight=True,
            ),
            actions=[
                ft.TextButton("بعداً پرداخت می‌کنم", on_click=close_and_go),
                ft.Button("💳 پرداخت آنلاین", on_click=do_pay),
            ],
        )

        self.page_ref.overlay.append(dialog)
        dialog.open = True
        self.page_ref.update()
