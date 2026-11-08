import flet as ft
from .. import api_client


class LoginScreen(ft.View):
    def __init__(self, page: ft.Page, on_login_success):
        self.page_ref = page
        self.on_login_success = on_login_success

        self.username_input = ft.TextField(label="نام کاربری", width=300, rtl=True)
        self.password_input = ft.TextField(
            label="رمز عبور", width=300, password=True,
            can_reveal_password=True, rtl=True
        )
        self.error_text = ft.Text(color=ft.Colors.RED, size=13)

        super().__init__(
            route="/login",
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("ورود به BijanStore", size=24, weight=ft.FontWeight.BOLD),
                            ft.Text("برای ادامه خرید وارد شوید", color=ft.Colors.GREY),
                            self.username_input,
                            self.password_input,
                            self.error_text,
                            ft.Button("ورود", on_click=self.do_login, width=300),
                            ft.TextButton(
                                "حساب ندارید؟ ثبت‌نام کنید",
                                on_click=lambda e: self.page_ref.go("/register"),
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=15,
                    ),
                    alignment=ft.Alignment.CENTER,
                    expand=True,
                    padding=40,
                )
            ],
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def do_login(self, e):
        self.error_text.value = ""

        success, message = api_client.login(
            self.username_input.value.strip(),
            self.password_input.value
        )

        if success:
            self.page_ref.snack_bar = ft.SnackBar(ft.Text(message))
            self.page_ref.snack_bar.open = True
            self.on_login_success()
        else:
            self.error_text.value = message